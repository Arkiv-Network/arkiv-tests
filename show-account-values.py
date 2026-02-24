import argparse
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


def main():
    parser = argparse.ArgumentParser(description="Show account balances derived from a mnemonic")
    parser.add_argument("--count", type=int, default=int(os.environ.get("ACCOUNT_COUNT", DEFAULT_COUNT)),
                        help=f"Number of addresses to derive (default: {DEFAULT_COUNT})")
    parser.add_argument("--rpc-url", type=str, default=os.environ.get("RPC_URL", "http://localhost:8545"),
                        help="RPC URL (default: http://localhost:8545)")
    args = parser.parse_args()

    addresses = load_addresses()

    connection_response = rpc_post(args.rpc_url, "web3_clientVersion")

    current_block_res = rpc_post(args.rpc_url, "eth_blockNumber")
    current_block = -1
    if current_block_res and 'result' in current_block_res:
        print(f"Current Block Number: {int(current_block_res['result'], 16)}\n")
        current_block = int(current_block_res['result'], 16)

    if current_block <= 0:
        raise ConnectionError(f"❌ RPC at {args.rpc_url} is not responding with valid block number. Check if the node is running and accessible.")

    current_block_hex = hex(current_block)

    if connection_response and 'result' in connection_response:
        print(f"✅ Connected to RPC at {args.rpc_url}")
        print(f"   Node Version: {connection_response['result']}\n")
        print(f"{'Address':<45} | {'Balance (ETH)'}")
        print("-" * 65)

        for address in addresses:
            try:
                response = rpc_post(args.rpc_url, "eth_getBalance", [address, current_block_hex])

                if response and 'result' in response:
                    hex_balance = response['result']
                    balance_wei = int(hex_balance, 16)
                    print(f"{address} | {balance_wei} ETH")
                elif response and 'error' in response:
                    print(f"{address} | RPC Error: {response['error']['message']}")
                else:
                    print(f"{address} | No response")

            except Exception as e:
                print(f"{address} | Error: {str(e)}")

        # Print nonces (transaction count) for each address
        print("\nNonces (latest)")
        print(f"{'Address':<45} | {'Nonce'}")
        print("-" * 65)

        for address in addresses:
            try:
                response = rpc_post(args.rpc_url, "eth_getTransactionCount", [address, current_block_hex])
                if response and 'result' in response:
                    hex_nonce = response['result']
                    nonce = int(hex_nonce, 16)
                    print(f"{address} | {nonce}")
                elif response and 'error' in response:
                    print(f"{address} | RPC Error: {response['error']['message']}")
                else:
                    print(f"{address} | No response")
            except Exception as e:
                print(f"{address} | Error: {str(e)}")

    else:
        raise ConnectionError(f"❌ Failed to connect to RPC at {args.rpc_url}")


if __name__ == "__main__":
    main()