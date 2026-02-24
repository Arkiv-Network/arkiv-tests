import argparse
import json
import os

import requests
from eth_account import Account

Account.enable_unaudited_hdwallet_features()

DEFAULT_COUNT = 10
DEFAULT_SNAPSHOT_FILE = "account-values-snapshot.json"

def load_addresses():
    with open("test-accounts.txt", "r") as f:
        return [line.strip() for line in f.readlines()]

def rpc_post(rpc_url, method, params=None):
    """Helper function to send JSON-RPC POST requests"""
    if params is None:
        params = []
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    try:
        response = requests.post(rpc_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return None


def main():
    parser = argparse.ArgumentParser(description="Show account balances derived from a mnemonic")
    parser.add_argument("--count", type=int, default=int(os.environ.get("ACCOUNT_COUNT", DEFAULT_COUNT)),
                        help=f"Number of addresses to derive (default: {DEFAULT_COUNT})")
    parser.add_argument("--rpc-url", type=str, default=os.environ.get("RPC_URL", "http://localhost:8545"),
                        help="RPC URL (default: http://localhost:8545)")
    parser.add_argument("--snapshot-file", type=str,
                        default=os.environ.get("ACCOUNT_VALUES_SNAPSHOT_FILE", DEFAULT_SNAPSHOT_FILE),
                        help=f"Snapshot file path (default: {DEFAULT_SNAPSHOT_FILE})")
    args = parser.parse_args()

    addresses = load_addresses()

    connection_response = rpc_post(args.rpc_url, "web3_clientVersion")

    current_block_res = rpc_post(args.rpc_url, "eth_blockNumber")
    current_block = -1
    if current_block_res and 'result' in current_block_res:
        current_block = int(current_block_res['result'], 16)

    if current_block <= 0:
        raise ConnectionError(f"❌ RPC at {args.rpc_url} is not responding with valid block number. Check if the node is running and accessible.")

    current_block_hex = hex(current_block)

    if connection_response and 'result' in connection_response:
        current_values = {}
        for address in addresses:
            try:
                balance_response = rpc_post(args.rpc_url, "eth_getBalance", [address, current_block_hex])
                nonce_response = rpc_post(args.rpc_url, "eth_getTransactionCount", [address, current_block_hex])
                if (
                    balance_response and 'result' in balance_response
                    and nonce_response and 'result' in nonce_response
                ):
                    current_values[address] = {
                        "balance_wei": int(balance_response['result'], 16),
                        "nonce": int(nonce_response['result'], 16),
                    }
            except Exception as e:
                raise RuntimeError(f"Failed to fetch account data for {address}: {str(e)}") from e

        previous_values = {}
        if os.path.exists(args.snapshot_file):
            with open(args.snapshot_file, "r") as f:
                previous_values = json.load(f)

        total_gas_used_wei = 0
        total_transactions_done = 0
        for address, values in current_values.items():
            previous = previous_values.get(address)
            if previous is None:
                continue
            total_gas_used_wei += max(0, previous["balance_wei"] - values["balance_wei"])
            total_transactions_done += max(0, values["nonce"] - previous["nonce"])

        print(f"Accounts: {len(current_values)}")
        print(f"Total gas used (wei): {total_gas_used_wei}")
        print(f"Total transactions done: {total_transactions_done}")

        with open(args.snapshot_file, "w") as f:
            json.dump(current_values, f, indent=2)

    else:
        raise ConnectionError(f"❌ Failed to connect to RPC at {args.rpc_url}")


if __name__ == "__main__":
    main()
