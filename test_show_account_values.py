import io
import importlib.util
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

eth_account_module = types.ModuleType("eth_account")


class _Account:
    @staticmethod
    def enable_unaudited_hdwallet_features():
        return None


eth_account_module.Account = _Account
sys.modules["eth_account"] = eth_account_module

spec = importlib.util.spec_from_file_location(
    "show_account_values",
    "/home/runner/work/arkiv-tests/arkiv-tests/show-account-values.py",
)
show_account_values = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(show_account_values)


class ShowAccountValuesTest(unittest.TestCase):
    def test_saves_snapshot_then_uses_it_for_totals(self):
        addresses = ["0xabc", "0xdef"]
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshot_file = f"{tmp_dir}/account-values-snapshot.json"
            state = {
                "0xabc": {"balance_wei": 100, "nonce": 1},
                "0xdef": {"balance_wei": 200, "nonce": 2},
            }

            def fake_rpc_post(_rpc_url, method, params=None):
                if method == "web3_clientVersion":
                    return {"result": "test-node"}
                if method == "eth_blockNumber":
                    return {"result": hex(10)}
                if method == "eth_getBalance":
                    return {"result": hex(state[params[0]]["balance_wei"])}
                if method == "eth_getTransactionCount":
                    return {"result": hex(state[params[0]]["nonce"])}
                return None

            with (
                patch.object(show_account_values, "load_addresses", return_value=addresses),
                patch.object(show_account_values, "rpc_post", side_effect=fake_rpc_post),
                patch(
                    "sys.argv",
                    ["show-account-values.py", "--rpc-url", "http://test", "--snapshot-file", snapshot_file],
                ),
            ):
                first_output = io.StringIO()
                with redirect_stdout(first_output):
                    show_account_values.main()

            self.assertIn("Accounts: 2", first_output.getvalue())
            self.assertIn("Total gas used (wei): 0", first_output.getvalue())
            self.assertIn("Total transactions done: 0", first_output.getvalue())

            state["0xabc"] = {"balance_wei": 90, "nonce": 3}
            state["0xdef"] = {"balance_wei": 180, "nonce": 4}

            with (
                patch.object(show_account_values, "load_addresses", return_value=addresses),
                patch.object(show_account_values, "rpc_post", side_effect=fake_rpc_post),
                patch(
                    "sys.argv",
                    ["show-account-values.py", "--rpc-url", "http://test", "--snapshot-file", snapshot_file],
                ),
            ):
                second_output = io.StringIO()
                with redirect_stdout(second_output):
                    show_account_values.main()

            self.assertIn("Accounts: 2", second_output.getvalue())
            self.assertIn("Total gas used (wei): 30", second_output.getvalue())
            self.assertIn("Total transactions done: 4", second_output.getvalue())


if __name__ == "__main__":
    unittest.main()
