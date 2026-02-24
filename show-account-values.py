import argparse
import json
import os

import requests
from eth_account import Account

Account.enable_unaudited_hdwallet_features()

DEFAULT_COUNT = 10

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


def fetch_account_values(rpc_url, addresses, block_hex):
    """Fetch balances and nonces for all addresses at a given block."""
    accounts = {}
    for address in addresses:
        balance = 0
        nonce = 0
        try:
            bal_response = rpc_post(rpc_url, "eth_getBalance", [address, block_hex])
            if bal_response and 'result' in bal_response:
                balance = int(bal_response['result'], 16)
        except Exception as e:
            print(f"⚠️  Error fetching balance for {address}: {e}")
        try:
            nonce_response = rpc_post(rpc_url, "eth_getTransactionCount", [address, block_hex])
            if nonce_response and 'result' in nonce_response:
                nonce = int(nonce_response['result'], 16)
        except Exception as e:
            print(f"⚠️  Error fetching nonce for {address}: {e}")
        accounts[address] = {"balance": balance, "nonce": nonce}
    return accounts


def main():
    parser = argparse.ArgumentParser(description="Show account balances derived from a mnemonic")
    parser.add_argument("--count", type=int, default=int(os.environ.get("ACCOUNT_COUNT", DEFAULT_COUNT)),
                        help=f"Number of addresses to derive (default: {DEFAULT_COUNT})")
    parser.add_argument("--rpc-url", type=str, default=os.environ.get("RPC_URL", "http://localhost:8545"),
                        help="RPC URL (default: http://localhost:8545)")
    parser.add_argument("--save", type=str, default=None,
                        help="Save account values to a JSON file")
    parser.add_argument("--compare", type=str, default=None,
                        help="Compare current values against a previously saved JSON file")
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

    if not (connection_response and 'result' in connection_response):
        raise ConnectionError(f"❌ Failed to connect to RPC at {args.rpc_url}")

    print(f"✅ Connected to RPC at {args.rpc_url}")
    print(f"   Node Version: {connection_response['result']}")
    print(f"   Current Block Number: {current_block}\n")

    accounts = fetch_account_values(args.rpc_url, addresses, current_block_hex)

    if args.save:
        with open(args.save, "w") as f:
            json.dump(accounts, f, indent=2)
        print(f"💾 Saved account values to {args.save}")

    total_gas_used = 0
    total_transactions = 0

    if args.compare:
        with open(args.compare, "r") as f:
            saved_accounts = json.load(f)
        for address in addresses:
            if address in saved_accounts and address in accounts:
                balance_before = saved_accounts[address]["balance"]
                nonce_before = saved_accounts[address]["nonce"]
                balance_after = accounts[address]["balance"]
                nonce_after = accounts[address]["nonce"]
                total_gas_used += balance_before - balance_after
                total_transactions += nonce_after - nonce_before
    else:
        for address in addresses:
            if address in accounts:
                total_transactions += accounts[address]["nonce"]

    print("📊 Account Summary")
    print(f"   Number of accounts: {len(accounts)}")
    print(f"   Total gas used (wei): {total_gas_used}")
    print(f"   Total transactions: {total_transactions}")


if __name__ == "__main__":
    main()