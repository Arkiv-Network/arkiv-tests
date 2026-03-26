import importlib.util
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "gather-metrics.py"


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


def load_gather_metrics_module():
    requests_module = types.ModuleType("requests")

    class RequestException(Exception):
        pass

    requests_module.RequestException = RequestException
    requests_module.get = lambda *args, **kwargs: None
    requests_module.post = lambda *args, **kwargs: None

    influxdb_client_module = types.ModuleType("influxdb_client")
    influxdb_client_module.Point = DummyPoint

    influxdb_client_client_module = types.ModuleType("influxdb_client.client")
    influxdb_client_async_module = types.ModuleType(
        "influxdb_client.client.influxdb_client_async"
    )

    class InfluxDBClientAsync:
        pass

    influxdb_client_async_module.InfluxDBClientAsync = InfluxDBClientAsync

    prometheus_client_module = types.ModuleType("prometheus_client")
    prometheus_parser_module = types.ModuleType("prometheus_client.parser")
    prometheus_parser_module.text_string_to_metric_families = lambda text: []

    sys.modules["requests"] = requests_module
    sys.modules["influxdb_client"] = influxdb_client_module
    sys.modules["influxdb_client.client"] = influxdb_client_client_module
    sys.modules["influxdb_client.client.influxdb_client_async"] = (
        influxdb_client_async_module
    )
    sys.modules["prometheus_client"] = prometheus_client_module
    sys.modules["prometheus_client.parser"] = prometheus_parser_module

    spec = importlib.util.spec_from_file_location("gather_metrics_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GatherMetricsTests(unittest.TestCase):
    def setUp(self):
        self.module = load_gather_metrics_module()
        self.sender_address = "0x" + ("ab" * 20)
        self.module.OP_NODE_L1_RPC_URL = "http://127.0.0.1:15900"
        self.module.OP_NODE_L1_ADDRESS = self.sender_address
        self.module.OP_NODE_L1_START_BLOCK = 0
        self.module.l1_tx_metrics_state = {
            "last_scanned_block": None,
            "transactions_total": {},
            "gas_used_total": {},
        }

    def test_normalize_eth_address_lowercases_valid_addresses(self):
        self.assertEqual(
            self.module.normalize_eth_address(self.sender_address.upper()),
            self.sender_address,
        )
        self.assertEqual(self.module.normalize_eth_address("not-an-address"), "")

    def test_collect_l1_sender_points_tracks_transactions_and_gas(self):
        other_address = "0x" + ("cd" * 20)
        transaction_hash = "0x" + ("12" * 32)

        responses = {
            ("eth_blockNumber", ()): "0x2",
            ("eth_getBlockByNumber", ("0x0", True)): {"transactions": []},
            ("eth_getBlockByNumber", ("0x1", True)): {
                "transactions": [
                    {"hash": transaction_hash, "from": self.sender_address.upper(), "to": other_address},
                    {"hash": "0x" + ("34" * 32), "from": other_address, "to": self.sender_address},
                ]
            },
            ("eth_getBlockByNumber", ("0x2", True)): {"transactions": []},
            ("eth_getBlockReceipts", ("0x1",)): [
                {"transactionHash": transaction_hash, "gasUsed": "0x5208"},
            ],
        }

        def fake_rpc(url, method, params):
            return responses[(method, tuple(params))]

        self.module.call_json_rpc = fake_rpc

        points = self.module.collect_l1_sender_points_sync()
        measurements = [point.measurement for point in points]

        self.assertEqual(self.module.l1_tx_metrics_state["transactions_total"]["op-node"], 1)
        self.assertEqual(self.module.l1_tx_metrics_state["gas_used_total"]["op-node"], 21000)
        self.assertEqual(self.module.l1_tx_metrics_state["last_scanned_block"], 2)
        self.assertIn("arkiv_l1_transaction_gas_used", measurements)
        self.assertIn("arkiv_l1_transactions_total", measurements)
        self.assertIn("arkiv_l1_gas_used_total", measurements)
        self.assertIn("arkiv_l1_last_scanned_block", measurements)

        tx_point = next(
            point for point in points if point.measurement == "arkiv_l1_transaction_gas_used"
        )
        self.assertEqual(tx_point.tags["component"], "op-node")
        self.assertEqual(tx_point.tags["sender"], self.sender_address)
        self.assertEqual(tx_point.fields["value"], 21000.0)

        points = self.module.collect_l1_sender_points_sync()
        self.assertEqual(self.module.l1_tx_metrics_state["transactions_total"]["op-node"], 1)
        self.assertEqual(self.module.l1_tx_metrics_state["gas_used_total"]["op-node"], 21000)
        self.assertEqual(
            [point.measurement for point in points],
            [
                "arkiv_l1_transactions_total",
                "arkiv_l1_gas_used_total",
                "arkiv_l1_last_scanned_block",
            ],
        )


if __name__ == "__main__":
    unittest.main()
