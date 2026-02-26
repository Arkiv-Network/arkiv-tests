import argparse
import json
import os
import requests

def load_addresses(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Accounts file not found: {file_path}")
    with open(file_path, "r") as f:
        # Filter out empty lines
        return [line.strip() for line in f.readlines() if line.strip()]

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
    except requests.exceptions.RequestException:
        return None

def fetch_account_values(rpc_url, addresses, block_hex):
    """Fetch balances and nonces for all addresses at a given block."""
    accounts = {}
    for address in addresses:
        balance = 0
        nonce = 0

        # Fetch Balance
        try:
            bal_response = rpc_post(rpc_url, "eth_getBalance", [address, block_hex])
            if bal_response and 'result' in bal_response:
                balance = int(bal_response['result'], 16)
        except Exception as e:
            print(f"⚠️  Error fetching balance for {address}: {e}")

        # Fetch Nonce
        try:
            nonce_response = rpc_post(rpc_url, "eth_getTransactionCount", [address, block_hex])
            if nonce_response and 'result' in nonce_response:
                nonce = int(nonce_response['result'], 16)
        except Exception as e:
            print(f"⚠️  Error fetching nonce for {address}: {e}")

        accounts[address] = {"balance": balance, "nonce": nonce}
    return accounts

def main():
    parser = argparse.ArgumentParser(description="Fetch and aggregate Ethereum account balances and nonces.")
    parser.add_argument("--accounts-file", type=str, default="test-accounts.txt",
                        help="Text file containing one Ethereum address per line (default: test-accounts.txt)")
    parser.add_argument("--rpc-url", type=str, default=os.environ.get("RPC_URL", "http://localhost:8545"),
                        help="RPC URL (default: http://localhost:8545)")
    parser.add_argument("--save", type=str, default=None,
                        help="Save strictly flat, numeric metrics to a JSON file for testing")
    parser.add_argument("--save-to-compare", type=str, default=os.environ.get("SAVE_FILE_COMPARE", "results_to_compare.json"),
                        help="Save raw account data for future comparison (default: results_to_compare.json)")
    parser.add_argument("--compare", type=str, default=None,
                        help="Compare current values against a previously saved JSON file")
    args = parser.parse_args()

    addresses = load_addresses(args.accounts_file)

    connection_response = rpc_post(args.rpc_url, "web3_clientVersion")
    current_block_res = rpc_post(args.rpc_url, "eth_blockNumber")

    current_block = -1
    if current_block_res and 'result' in current_block_res:
        current_block = int(current_block_res['result'], 16)

    # Block 0 (Genesis) is valid, so check if less than 0
    if current_block < 0:
        raise ConnectionError(f"❌ RPC at {args.rpc_url} is not responding with valid block number.")

    if not (connection_response and 'result' in connection_response):
        raise ConnectionError(f"❌ Failed to connect to RPC at {args.rpc_url}")

    current_block_hex = hex(current_block)

    print(f"✅ Connected to RPC at {args.rpc_url}")
    print(f"   Node Version: {connection_response['result']}")
    print(f"   Current Block Number: {current_block}\n")

    accounts = fetch_account_values(args.rpc_url, addresses, current_block_hex)

    net_balance_decrease = 0
    total_transactions = 0
    accounts_with_tx = 0

    if args.compare:
        try:
            with open(args.compare, "r") as f:
                saved_accounts = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to read compare file {args.compare}: {e}")

        for address in addresses:
            if address in saved_accounts and address in accounts:
                balance_before = saved_accounts[address]["balance"]
                nonce_before = saved_accounts[address]["nonce"]
                balance_after = accounts[address]["balance"]
                nonce_after = accounts[address]["nonce"]

                net_balance_decrease += (balance_before - balance_after)
                total_transactions += (nonce_after - nonce_before)

                # Check for *new* transactions since the snapshot
                if nonce_after > nonce_before:
                    accounts_with_tx += 1
    else:
        for address in addresses:
            if address in accounts:
                nonce = accounts[address]["nonce"]
                total_transactions += nonce
                if nonce > 0:
                    accounts_with_tx += 1

    # STRICTLY FLAT, NUMERIC-ONLY DICTIONARY
    test_metrics = {
        "blockNumberArkiv": current_block,
        "numAddressesChecked": len(accounts),
        "accountsWithTx": accounts_with_tx,
        "netBalanceDecreaseWei": net_balance_decrease,
        "totalTransactions": total_transactions,
    }

    if args.save:
        to_write = test_metrics
        if os.path.exists(args.save):
            try:
                with open(args.save, "r") as f:
                    existing = json.load(f)
                if isinstance(existing, dict):
                    to_write = {**existing, **test_metrics}
                    print(f"🔀 Updated existing save file {args.save} with current aggregates")
                else:
                    print(f"⚠️  Existing save file {args.save} not a JSON object; overwriting.")
            except Exception as e:
                print(f"⚠️  Failed to read {args.save}: {e}; overwriting.")

        try:
            with open(args.save, "w") as f:
                json.dump(to_write, f, indent=2)
            print(f"💾 Saved flat test metrics to {args.save}")
        except Exception as e:
            print(f"❌ Failed to write {args.save}: {e}")

    if args.save_to_compare:
        try:
            with open(args.save_to_compare, "w") as f:
                json.dump(accounts, f, indent=2)
            print(f"💾 Saved raw account data to {args.save_to_compare}")
        except Exception as e:
            print(f"❌ Failed to write {args.save_to_compare}: {e}")

    # Print the account summary
    print("\n📊 Account Summary")
    print(f"   Number of accounts: {len(accounts)}")
    print(f"   Accounts with txs (in scope): {accounts_with_tx}")
    print(f"   Net balance decrease (wei): {net_balance_decrease}")
    print(f"   Total transactions (in scope): {total_transactions}")

if __name__ == "__main__":
    main()