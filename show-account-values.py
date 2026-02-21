import argparse
import os

import requests
from eth_account import Account

Account.enable_unaudited_hdwallet_features()

DEFAULT_COUNT = 10


def build_account_path(user_index: int) -> str:
    instance_index = 0
    return f"m/44'/60'/{instance_index}'/0/{user_index}"


def derive_addresses(mnemonic: str, count: int) -> list[str]:
    addresses = []
    for i in range(count):
        account_path = build_account_path(i)
        account = Account.from_mnemonic(mnemonic, account_path=account_path)
        addresses.append(account.address)
    return addresses


def rpc_post(rpc_url, method, params=[]):
    """Helper function to send JSON-RPC POST requests"""
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
    parser.add_argument("--mnemonic", type=str, default=os.environ.get("MNEMONIC", ""),
                        help="Mnemonic phrase (or set MNEMONIC env var)")
    parser.add_argument("--count", type=int, default=int(os.environ.get("ACCOUNT_COUNT", DEFAULT_COUNT)),
                        help=f"Number of addresses to derive (default: {DEFAULT_COUNT})")
    parser.add_argument("--rpc-url", type=str, default=os.environ.get("RPC_URL", "http://localhost:8545"),
                        help="RPC URL (default: http://localhost:8545)")
    args = parser.parse_args()

    if not args.mnemonic:
        raise ValueError("Mnemonic is required. Use --mnemonic or set MNEMONIC env var.")

    addresses = derive_addresses(args.mnemonic, args.count)

    connection_response = rpc_post(args.rpc_url, "web3_clientVersion")

    if connection_response and 'result' in connection_response:
        print(f"✅ Connected to RPC at {args.rpc_url}")
        print(f"   Node Version: {connection_response['result']}\n")
        print(f"{'Address':<45} | {'Balance (ETH)'}")
        print("-" * 65)

        for address in addresses:
            try:
                response = rpc_post(args.rpc_url, "eth_getBalance", [address, "latest"])

                if 'result' in response:
                    hex_balance = response['result']
                    balance_wei = int(hex_balance, 16)
                    balance_eth = balance_wei / 10**18
                    print(f"{address} | {balance_eth} ETH")
                elif 'error' in response:
                    print(f"{address} | RPC Error: {response['error']['message']}")

            except Exception as e:
                print(f"{address} | Error: {str(e)}")
    else:
        raise ConnectionError(f"❌ Failed to connect to RPC at {args.rpc_url}")


if __name__ == "__main__":
    main()