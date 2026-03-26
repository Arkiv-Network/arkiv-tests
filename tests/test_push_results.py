import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "push-results.py"


def load_push_results_module():
    spec = importlib.util.spec_from_file_location("push_results_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PushResultsTests(unittest.TestCase):
    def setUp(self):
        self.module = load_push_results_module()

    def test_collect_l1_metrics_with_valid_data(self):
        values = {
            "arkiv_l1_transactions_total": 3,
            "arkiv_mainnet_gas_price": 21_000_000_000_000,
        }

        def fake_query(test_name, measurement):
            self.assertEqual(test_name, "sample-test")
            return values.get(measurement)

        with mock.patch.object(
            self.module, "query_last_metric_total", side_effect=fake_query
        ):
            metrics = self.module.collect_l1_result_metrics("sample-test")

        self.assertEqual(metrics["totalTransactionsL1"], {"value": 3})
        self.assertEqual(
            metrics["gasSpentL1"],
            {"value": 21_000_000_000_000, "display": "0.000021"},
        )

    def test_query_last_metric_total_escapes_flux_strings(self):
        captured = {}

        class FakeRecord(dict):
            pass

        class FakeTable:
            records = [FakeRecord(_value=5)]

        class FakeQueryApi:
            def query(self, org, query):
                captured["org"] = org
                captured["query"] = query
                return [FakeTable()]

        class FakeInfluxDBClient:
            def __init__(self, url, token, org):
                captured["client_args"] = {"url": url, "token": token, "org": org}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def query_api(self):
                return FakeQueryApi()

        with mock.patch.object(self.module, "InfluxDBClient", FakeInfluxDBClient):
            value = self.module.query_last_metric_total(
                'sample"test\nname', 'metric"value'
            )

        self.assertEqual(value, 5)
        self.assertEqual(captured["org"], self.module.INFLUX_ORG)
        self.assertIn('r["_measurement"] == "metric\\"value"', captured["query"])
        self.assertIn('r["test"] == "sample\\"test\\nname"', captured["query"])

    def test_push_results_merges_l1_metrics(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as results_file:
            json.dump({"existingMetric": {"value": 7}}, results_file)
            results_file_path = results_file.name

        captured = {}

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                return None

        def fake_post(url, json):
            captured["url"] = url
            captured["payload"] = json
            return FakeResponse()

        with (
            mock.patch.object(
                self.module,
                "collect_l1_result_metrics",
                return_value={
                    "totalTransactionsL1": {"value": 3},
                    "gasSpentL1": {"value": 21_000_000_000_000, "display": "0.000021"},
                },
            ),
            mock.patch.object(self.module.requests, "post", side_effect=fake_post),
        ):
            self.module.push_results(
                "https://tracker.example",
                "sample-test",
                results_file_path,
                120,
            )

        self.assertEqual(
            captured["url"], "https://tracker.example/test/sample-test/results"
        )
        self.assertEqual(
            captured["payload"],
            {
                "parameters": {
                    "existingMetric": {"value": 7},
                    "totalTransactionsL1": {"value": 3},
                    "gasSpentL1": {
                        "value": 21_000_000_000_000,
                        "display": "0.000021",
                    },
                },
                "seconds": 120,
            },
        )


if __name__ == "__main__":
    unittest.main()
