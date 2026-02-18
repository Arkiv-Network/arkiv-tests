import requests
import json
import sys

def get_mempool_transactions(rpc_url):
    """
    Fetches transactions from the Geth mempool using txpool_content.
    """
    headers = {'Content-Type': 'application/json'}

    # JSON-RPC payload for txpool_content
    payload = {
        "jsonrpc": "2.0",
        "method": "txpool_content",
        "params": [],
        "id": 1
    }

    try:
        print(f"Connecting to {rpc_url}...")
        response = requests.post(rpc_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()

        data = response.json()

        if 'error' in data:
            print(f"RPC Error: {data['error']}")
            return

        result = data.get('result', {})

        # txpool_content returns two fields: 'pending' and 'queued'
        pending_txs = result.get('pending', {})
        queued_txs = result.get('queued', {})

        print(f"\n--- Mempool Snapshot ---")
        print(f"Pending Accounts: {len(pending_txs)}")
        print(f"Queued Accounts:  {len(queued_txs)}\n")

        # Function to process and print transaction lists
        def print_tx_list(tx_source, label):
            count = 0
            # The structure is { 'from_address': { 'nonce': { tx_object } } }
            for from_address, nonces in tx_source.items():
                for nonce, tx in nonces.items():
                    count += 1

                    # Extract specific fields safely
                    tx_hash = tx.get('hash', 'N/A')
                    to_address = tx.get('to', 'Contract Creation') # None usually means contract creation
                    value_wei = tx.get('value', '0x0')
                    gas_price = tx.get('gasPrice', '0x0')
                    input_data = tx.get('input', '0x')

                    # Shorten input data to 32 bytes (64 hex characters + 0x prefix)
                    short_input = input_data[:66]
                    if len(input_data) > 66:
                        short_input += "..."

                    print(f"[{label}] Tx Hash: {tx_hash}")
                    print(f"  From:      {from_address}")
                    print(f"  To:        {to_address}")
                    print(f"  Value:     {int(value_wei, 16)} wei")
                    print(f"  Gas Price: {int(gas_price, 16) / 10**9} Gwei")
                    print(f"  Nonce:     {nonce}")
                    print(f"  Call Data: {short_input} (First 32 bytes)")
                    print("-" * 60)
            return count

        print(f"--- Pending Transactions (Ready to be mined) ---")
        p_count = print_tx_list(pending_txs, "PENDING")

        print(f"--- Queued Transactions (Future nonce or low cost) ---")
        q_count = print_tx_list(queued_txs, "QUEUED")

        print(f"\nTotal Transactions Listed: {p_count + q_count}")

    except requests.exceptions.MissingSchema:
        print(f"Error: Invalid URL '{rpc_url}'. Make sure to include http:// or https://")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the node. Ensure Geth is running and HTTP-RPC is enabled.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Default to localhost if no argument is provided
    node_url = "http://localhost:8545"

    # Check if an argument was passed
    if len(sys.argv) > 1:
        node_url = sys.argv[1]

    get_mempool_transactions(node_url)