import contextlib
import io
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
        self.batcher_address = "0x" + ("bc" * 20)
        self.proposer_address = "0x" + ("de" * 20)
        self.module.OP_NODE_L1_RPC_URL = "http://127.0.0.1:15900"
        self.module.OP_NODE_L1_ADDRESS = self.sender_address
        self.module.OP_BATCHER_L1_ADDRESS = ""
        self.module.OP_PROPOSER_L1_ADDRESS = ""
        self.module.OP_NODE_L1_START_BLOCK = 0
        self.module.l1_tx_metrics_state = {
            "last_scanned_block": None,
            "transactions_total": {},
            "gas_used_total": {},
            "simulated_mainnet_spending": {},
            "simulated_eth_spend_wei_total": 0,
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
        self.module.GAS_BASE_NETWORK = "https://mainnet.rpc-node.dev.golem.network/"

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
            ("eth_gasPrice", ()): "0x3b9aca00",
        }

        def fake_rpc(url, method, params):
            return responses[(method, tuple(params))]

        self.module.call_json_rpc = fake_rpc

        points = self.module.collect_l1_sender_points_sync()
        measurements = [point.measurement for point in points]

        self.assertEqual(self.module.l1_tx_metrics_state["transactions_total"]["op-node"], 1)
        self.assertEqual(self.module.l1_tx_metrics_state["gas_used_total"]["op-node"], 21000)
        self.assertEqual(
            self.module.l1_tx_metrics_state["simulated_mainnet_spending"]["op-node"],
            21_000_000_000_000,
        )
        self.assertEqual(
            self.module.l1_tx_metrics_state["simulated_eth_spend_wei_total"],
            21_000_000_000_000,
        )
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

    def test_collect_l1_sender_points_tracks_multiple_components(self):
        batcher_hash = "0x" + ("12" * 32)
        proposer_hash = "0x" + ("34" * 32)
        self.module.OP_NODE_L1_ADDRESS = ""
        self.module.OP_BATCHER_L1_ADDRESS = self.batcher_address
        self.module.OP_PROPOSER_L1_ADDRESS = self.proposer_address
        self.module.GAS_BASE_NETWORK = ""

        responses = {
            ("eth_blockNumber", ()): "0x1",
            ("eth_getBlockByNumber", ("0x0", True)): {"transactions": []},
            ("eth_getBlockByNumber", ("0x1", True)): {
                "transactions": [
                    {"hash": batcher_hash, "from": self.batcher_address, "to": "0x" + ("ef" * 20)},
                    {"hash": proposer_hash, "from": self.proposer_address.upper(), "to": "0x" + ("01" * 20)},
                ]
            },
            ("eth_getBlockReceipts", ("0x1",)): [
                {"transactionHash": batcher_hash, "gasUsed": "0x5208"},
                {"transactionHash": proposer_hash, "gasUsed": "0x7530"},
            ],
        }

        def fake_rpc(url, method, params):
            return responses[(method, tuple(params))]

        self.module.call_json_rpc = fake_rpc

        points = self.module.collect_l1_sender_points_sync()

        self.assertEqual(self.module.l1_tx_metrics_state["transactions_total"]["op-batcher"], 1)
        self.assertEqual(self.module.l1_tx_metrics_state["transactions_total"]["op-proposer"], 1)
        self.assertEqual(self.module.l1_tx_metrics_state["gas_used_total"]["op-batcher"], 21000)
        self.assertEqual(self.module.l1_tx_metrics_state["gas_used_total"]["op-proposer"], 30000)
        self.assertEqual(self.module.l1_tx_metrics_state["simulated_mainnet_spending"], {})

        transaction_points = [
            point for point in points if point.measurement == "arkiv_l1_transaction_gas_used"
        ]
        total_points = [
            point for point in points if point.measurement == "arkiv_l1_transactions_total"
        ]
        self.assertEqual(len(transaction_points), 2)
        self.assertEqual(len(total_points), 2)
        self.assertEqual(
            {point.tags["component"] for point in total_points},
            {"op-batcher", "op-proposer"},
        )

    def test_collect_l1_sender_points_logs_matched_transactions_and_points(self):
        transaction_hash = "0x" + ("12" * 32)
        other_address = "0x" + ("cd" * 20)
        self.module.GAS_BASE_NETWORK = ""
        responses = {
            ("eth_blockNumber", ()): "0x1",
            ("eth_getBlockByNumber", ("0x0", True)): {"transactions": []},
            ("eth_getBlockByNumber", ("0x1", True)): {
                "transactions": [
                    {"hash": transaction_hash, "from": self.sender_address, "to": other_address},
                ]
            },
            ("eth_getBlockReceipts", ("0x1",)): [
                {"transactionHash": transaction_hash, "gasUsed": "0x5208"},
            ],
        }

        def fake_rpc(url, method, params):
            return responses[(method, tuple(params))]

        self.module.call_json_rpc = fake_rpc

        with io.StringIO() as stdout, contextlib.redirect_stdout(stdout):
            self.module.collect_l1_sender_points_sync()
            output = stdout.getvalue()

        self.assertIn(
            f"[l1-tracker] block 1: fetching receipts for {transaction_hash}",
            output,
        )
        self.assertIn(
            f"[l1-tracker] tx {transaction_hash}: component=op-node sender={self.sender_address}",
            output,
        )
        self.assertIn("cumulative_transactions=1 cumulative_gas_used=21000", output)
        self.assertIn("queued arkiv_l1_transaction_gas_used", output)
        self.assertIn("queued arkiv_l1_transactions_total", output)

    def test_collect_l1_sender_points_logs_unmatched_transaction_senders(self):
        other_address = "0x" + ("cd" * 20)
        self.module.OP_BATCHER_L1_ADDRESS = self.batcher_address
        self.module.OP_NODE_L1_ADDRESS = ""
        responses = {
            ("eth_blockNumber", ()): "0x1",
            ("eth_getBlockByNumber", ("0x0", True)): {"transactions": []},
            ("eth_getBlockByNumber", ("0x1", True)): {
                "transactions": [
                    {"hash": "0x" + ("56" * 32), "from": other_address, "to": self.batcher_address},
                ]
            },
        }

        def fake_rpc(url, method, params):
            return responses[(method, tuple(params))]

        self.module.call_json_rpc = fake_rpc

        with io.StringIO() as stdout, contextlib.redirect_stdout(stdout):
            self.module.collect_l1_sender_points_sync()
            output = stdout.getvalue()

        self.assertIn("[l1-tracker] block 1: scanned 1 transaction(s) but found no matches.", output)
        self.assertIn(f"tracked=op-batcher={self.batcher_address}", output)
        self.assertIn(f"seen_from={other_address}", output)

    def test_log_prepared_l1_points_logs_summary_and_queued_points(self):
        point = self.module.create_point(
            "arkiv_l1_transactions_total",
            2,
            {"component": "op-batcher", "sender": self.batcher_address},
        )

        with io.StringIO() as stdout, contextlib.redirect_stdout(stdout):
            self.module.log_prepared_l1_points(61, [point])
            output = stdout.getvalue()

        self.assertIn(
            "[l1-tracker] iteration 61: prepared 1 L1 point(s) for InfluxDB write.",
            output,
        )
        self.assertIn("measurements=arkiv_l1_transactions_total=1", output)
        self.assertIn("queued arkiv_l1_transactions_total", output)


    def test_collect_mainnet_gas_metrics_returns_total_spend(self):
        self.module.GAS_BASE_NETWORK = "https://mainnet.rpc-node.dev.golem.network/"
        self.module.l1_tx_metrics_state["simulated_eth_spend_wei_total"] = 21_000_000_000_000

        points = self.module.collect_mainnet_gas_metrics_sync()
        measurements = [point.measurement for point in points]

        self.assertIn("arkiv_mainnet_gas_price", measurements)
        gas_price_point = next(
            p for p in points if p.measurement == "arkiv_mainnet_gas_price"
        )
        self.assertEqual(gas_price_point.fields["value"], 21_000_000_000_000.0)

    def test_collect_mainnet_gas_metrics_computes_simulated_spending_metrics(self):
        self.module.GAS_BASE_NETWORK = "https://mainnet.rpc-node.dev.golem.network/"
        self.module.l1_tx_metrics_state["simulated_mainnet_spending"]["op-node"] = (
            21_000_000_000_000
        )
        self.module.l1_tx_metrics_state["simulated_eth_spend_wei_total"] = (
            21_000_000_000_000
        )

        points = self.module.collect_mainnet_gas_metrics_sync()
        measurements = [point.measurement for point in points]

        self.assertIn("arkiv_simulated_mainnet_spending", measurements)
        self.assertIn("arkiv_simulated_eth_spend", measurements)
        spend_wei_point = next(
            p for p in points if p.measurement == "arkiv_simulated_mainnet_spending"
        )
        spend_point = next(
            p for p in points if p.measurement == "arkiv_simulated_eth_spend"
        )
        self.assertEqual(spend_wei_point.tags["component"], "op-node")
        self.assertEqual(spend_wei_point.fields["value"], 21_000_000_000_000.0)
        self.assertEqual(spend_point.tags.get("component"), None)
        # 21000 gas * 1 gwei (1e9 wei) / 1e18 = 21000 * 1e-9 = 0.000021 ETH
        self.assertAlmostEqual(spend_point.fields["value"], 0.000021)

    def test_collect_mainnet_gas_metrics_emits_simulated_spending_for_batcher_and_proposer(self):
        self.module.GAS_BASE_NETWORK = "https://mainnet.rpc-node.dev.golem.network/"
        self.module.l1_tx_metrics_state["simulated_mainnet_spending"]["op-batcher"] = (
            21_000_000_000_000
        )
        self.module.l1_tx_metrics_state["simulated_mainnet_spending"]["op-proposer"] = (
            30_000_000_000_000
        )
        self.module.l1_tx_metrics_state["simulated_eth_spend_wei_total"] = (
            51_000_000_000_000
        )

        points = self.module.collect_mainnet_gas_metrics_sync()
        spend_points = {
            point.tags["component"]: point
            for point in points
            if point.measurement == "arkiv_simulated_mainnet_spending"
        }

        self.assertEqual(set(spend_points), {"op-batcher", "op-proposer"})
        self.assertEqual(spend_points["op-batcher"].fields["value"], 21_000_000_000_000.0)
        self.assertEqual(spend_points["op-proposer"].fields["value"], 30_000_000_000_000.0)
        eth_spend_points = [
            point for point in points if point.measurement == "arkiv_simulated_eth_spend"
        ]
        self.assertEqual(len(eth_spend_points), 1)
        self.assertEqual(eth_spend_points[0].tags.get("component"), None)
        self.assertAlmostEqual(eth_spend_points[0].fields["value"], 0.000051)

    def test_collect_mainnet_gas_metrics_empty_when_no_url(self):
        self.module.GAS_BASE_NETWORK = ""
        points = self.module.collect_mainnet_gas_metrics_sync()
        self.assertEqual(points, [])

    def test_collect_celestia_da_gas_metrics_returns_gas_price(self):
        self.module.CELENIUM_API_URL = "https://api-mainnet.celenium.io"
        self.module.fetch_celenium_gas_price = lambda: 0.004001
        self.module.da_metrics_state = {
            "last_da_data_size": 0,
            "simulated_da_spending_total": 0.0,
        }
        self.module.metrics_state["arkiv_da_data_size"] = 0

        points = self.module.collect_celestia_da_gas_metrics_sync()
        measurements = [point.measurement for point in points]

        self.assertIn("arkiv_celestia_gas_price", measurements)
        gas_price_point = next(
            p for p in points if p.measurement == "arkiv_celestia_gas_price"
        )
        self.assertAlmostEqual(gas_price_point.fields["value"], 0.004001)

    def test_collect_celestia_da_gas_metrics_computes_spending_on_size_change(self):
        self.module.CELENIUM_API_URL = "https://api-mainnet.celenium.io"
        self.module.fetch_celenium_gas_price = lambda: 0.004001
        self.module.fetch_celenium_pfb_estimate = lambda size: 100000
        self.module.da_metrics_state = {
            "last_da_data_size": 1000,
            "simulated_da_spending_total": 0.0,
        }
        self.module.metrics_state["arkiv_da_data_size"] = 2000

        points = self.module.collect_celestia_da_gas_metrics_sync()
        measurements = [point.measurement for point in points]

        self.assertIn("arkiv_celestia_gas_price", measurements)
        self.assertIn("arkiv_simulated_da_spending", measurements)
        spending_point = next(
            p for p in points if p.measurement == "arkiv_simulated_da_spending"
        )
        # 100000 * 0.004001 = 400.1
        self.assertAlmostEqual(spending_point.fields["value"], 400.1)
        self.assertEqual(self.module.da_metrics_state["last_da_data_size"], 2000)

    def test_collect_celestia_da_gas_metrics_no_spending_when_size_unchanged(self):
        self.module.CELENIUM_API_URL = "https://api-mainnet.celenium.io"
        self.module.fetch_celenium_gas_price = lambda: 0.004001
        self.module.da_metrics_state = {
            "last_da_data_size": 1000,
            "simulated_da_spending_total": 0.0,
        }
        self.module.metrics_state["arkiv_da_data_size"] = 1000

        points = self.module.collect_celestia_da_gas_metrics_sync()
        measurements = [point.measurement for point in points]

        self.assertIn("arkiv_celestia_gas_price", measurements)
        self.assertNotIn("arkiv_simulated_da_spending", measurements)

    def test_collect_celestia_da_gas_metrics_accumulates_spending(self):
        self.module.CELENIUM_API_URL = "https://api-mainnet.celenium.io"
        self.module.fetch_celenium_gas_price = lambda: 0.004001
        self.module.fetch_celenium_pfb_estimate = lambda size: 50000
        self.module.da_metrics_state = {
            "last_da_data_size": 1000,
            "simulated_da_spending_total": 100.0,
        }
        self.module.metrics_state["arkiv_da_data_size"] = 2000

        points = self.module.collect_celestia_da_gas_metrics_sync()
        spending_point = next(
            p for p in points if p.measurement == "arkiv_simulated_da_spending"
        )
        # 100.0 + 50000 * 0.004001 = 100.0 + 200.05 = 300.05
        self.assertAlmostEqual(spending_point.fields["value"], 300.05)

    def test_collect_celestia_da_gas_metrics_empty_when_no_url(self):
        self.module.CELENIUM_API_URL = ""
        points = self.module.collect_celestia_da_gas_metrics_sync()
        self.assertEqual(points, [])


if __name__ == "__main__":
    unittest.main()
