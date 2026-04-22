import importlib.util
import io
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "scrape-reth-metrics.py"


class DummyPoint:
    def __init__(self, measurement):
        self.measurement = measurement
        self.tags = {}
        self.fields = {}

    def tag(self, key, value):
        self.tags[key] = value
        return self

    def field(self, key, value):
        self.fields[key] = value
        return self


class DummySample:
    def __init__(self, name, labels, value):
        self.name = name
        self.labels = labels
        self.value = value


class DummyFamily:
    def __init__(self, samples):
        self.samples = samples


class DummyWriteApi:
    def __init__(self):
        self.writes = []

    def write(self, bucket, record):
        self.writes.append((bucket, list(record)))


class DummyClient:
    def __init__(self):
        self.write_api_instance = DummyWriteApi()
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True
        return False

    def write_api(self, write_options=None):  # noqa: ARG002
        return self.write_api_instance


def load_module(prom_text="", families=None):
    requests_module = types.ModuleType("requests")

    class RequestException(Exception):
        pass

    requests_module.RequestException = RequestException
    requests_module.get = lambda *args, **kwargs: None
    requests_module.post = lambda *args, **kwargs: None

    influxdb_client_module = types.ModuleType("influxdb_client")
    influxdb_client_module.Point = DummyPoint
    influxdb_client_module.InfluxDBClient = lambda **kwargs: DummyClient()

    influxdb_client_client_module = types.ModuleType("influxdb_client.client")
    influxdb_client_write_api_module = types.ModuleType(
        "influxdb_client.client.write_api"
    )
    influxdb_client_write_api_module.SYNCHRONOUS = object()

    prometheus_client_module = types.ModuleType("prometheus_client")
    prometheus_parser_module = types.ModuleType("prometheus_client.parser")
    families = families if families is not None else []
    prometheus_parser_module.text_string_to_metric_families = (
        lambda text: families if text == prom_text else []
    )

    sys.modules["requests"] = requests_module
    sys.modules["influxdb_client"] = influxdb_client_module
    sys.modules["influxdb_client.client"] = influxdb_client_client_module
    sys.modules["influxdb_client.client.write_api"] = (
        influxdb_client_write_api_module
    )
    sys.modules["prometheus_client"] = prometheus_client_module
    sys.modules["prometheus_client.parser"] = prometheus_parser_module

    spec = importlib.util.spec_from_file_location(
        "scrape_reth_metrics_under_test", MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ScrapeRethMetricsTests(unittest.TestCase):
    def setUp(self):
        self.families = [
            DummyFamily(
                [
                    DummySample(
                        "reth_block_height",
                        {"chain": "optimism"},
                        12345.0,
                    ),
                    DummySample(
                        "reth_pool_pending_transactions",
                        {},
                        7.0,
                    ),
                    # NaN should be skipped
                    DummySample("reth_should_skip", {}, float("nan")),
                ]
            )
        ]
        self.module = load_module(prom_text="dummy", families=self.families)
        self.module.JOB_NAME = "test-job"
        self.module.INSTANCE_NAME = "worker-1"

    def test_build_points_tags_and_filters(self):
        points = self.module.build_points("sequencer", "dummy")
        # NaN sample dropped
        self.assertEqual(len(points), 2)

        first = points[0]
        self.assertEqual(first.measurement, "reth_block_height")
        self.assertEqual(first.tags["test"], "test-job")
        self.assertEqual(first.tags["instance"], "worker-1")
        self.assertEqual(first.tags["node"], "sequencer")
        self.assertEqual(first.tags["component"], "op-reth")
        self.assertEqual(first.tags["chain"], "optimism")
        self.assertEqual(first.fields["value"], 12345.0)

        second = points[1]
        self.assertEqual(second.tags["node"], "sequencer")
        self.assertNotIn("chain", second.tags)
        self.assertEqual(second.fields["value"], 7.0)

    def test_resolve_targets_uses_env_overrides(self):
        with mock.patch.dict(
            "os.environ",
            {
                "RETH_SEQUENCER_METRICS_URL": "http://seq:6160/debug/metrics/prometheus",
                "RETH_VALIDATOR_METRICS_URL": "http://val:6060/debug/metrics/prometheus",
            },
            clear=False,
        ):
            targets = self.module.resolve_targets()
        self.assertEqual(
            targets,
            {
                "sequencer": "http://seq:6160/debug/metrics/prometheus",
                "validator": "http://val:6060/debug/metrics/prometheus",
            },
        )

    def test_resolve_targets_skips_blank_overrides(self):
        with mock.patch.dict(
            "os.environ",
            {"RETH_VALIDATOR_METRICS_URL": "   "},
            clear=False,
        ):
            targets = self.module.resolve_targets()
        self.assertIn("sequencer", targets)
        self.assertNotIn("validator", targets)

    def test_run_pushes_collected_points_then_stops(self):
        scraped_calls = []

        sequencer_points = [DummyPoint("reth_block_height").field("value", 1.0)]
        validator_points = [DummyPoint("reth_block_height").field("value", 2.0)]

        def fake_scrape(node, url):
            scraped_calls.append((node, url))
            return sequencer_points if node == "sequencer" else validator_points

        client = DummyClient()

        # Stop the loop after the first iteration by raising from sleep
        class Stop(Exception):
            pass

        def fake_sleep(_):
            raise Stop()

        self.module.SCRAPE_INTERVAL_SECONDS = 0.01
        self.module.INFLUX_BUCKET = "arkiv-tests"

        with mock.patch.dict(
            "os.environ",
            {
                "RETH_SEQUENCER_METRICS_URL": "http://seq/x",
                "RETH_VALIDATOR_METRICS_URL": "http://val/x",
            },
            clear=False,
        ):
            with self.assertRaises(Stop):
                self.module.run(
                    scrape_fn=fake_scrape,
                    sleep_fn=fake_sleep,
                    client_factory=lambda: client,
                )

        self.assertEqual(
            sorted(scraped_calls),
            [
                ("sequencer", "http://seq/x"),
                ("validator", "http://val/x"),
            ],
        )
        writes = client.write_api_instance.writes
        self.assertEqual(len(writes), 2)
        for bucket, _records in writes:
            self.assertEqual(bucket, "arkiv-tests")

    def test_run_continues_when_scrape_fails(self):
        def fake_scrape(node, url):
            if node == "sequencer":
                raise RuntimeError("boom")
            return [DummyPoint("reth_block_height").field("value", 2.0)]

        client = DummyClient()

        class Stop(Exception):
            pass

        def fake_sleep(_):
            raise Stop()

        self.module.SCRAPE_INTERVAL_SECONDS = 0.0

        captured_stdout = io.StringIO()
        with mock.patch.dict(
            "os.environ",
            {
                "RETH_SEQUENCER_METRICS_URL": "http://seq/x",
                "RETH_VALIDATOR_METRICS_URL": "http://val/x",
            },
            clear=False,
        ):
            with mock.patch("sys.stdout", captured_stdout):
                with self.assertRaises(Stop):
                    self.module.run(
                        scrape_fn=fake_scrape,
                        sleep_fn=fake_sleep,
                        client_factory=lambda: client,
                    )

        output = captured_stdout.getvalue()
        self.assertIn("failed to scrape sequencer", output)
        # Validator points must still be written even though sequencer failed.
        writes = client.write_api_instance.writes
        self.assertEqual(len(writes), 1)


if __name__ == "__main__":
    unittest.main()
