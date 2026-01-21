import json
import requests

# 1. Define the account data provided
with open('keys.json', 'r') as f:
    accounts = json.load(f)

# 2. Define RPC URL and Headers
rpc_url = "http://localhost:8545"
headers = {'Content-Type': 'application/json'}

def rpc_post(method, params=[]):
    """Helper function to send JSON-RPC POST requests"""
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

# 3. Check connection status (Mimicking w3.is_connected)
# We use 'web3_clientVersion' as a lightweight connectivity check
connection_response = rpc_post("web3_clientVersion")

if connection_response and 'result' in connection_response:
    print(f"✅ Connected to RPC at {rpc_url}")
    print(f"   Node Version: {connection_response['result']}\n")
    print(f"{'Address':<45} | {'Balance (ETH)'}")
    print("-" * 65)

    # 4. Loop through accounts and fetch balance
    for acc in accounts:
        address = acc["address"]

        try:
            # RPC Call: eth_getBalance
            # Params: [Address, Block Parameter ("latest")]
            response = rpc_post("eth_getBalance", [address, "latest"])

            if 'result' in response:
                # RPC returns balance as a hex string (e.g., "0x1a2...")
                hex_balance = response['result']

                # Convert Hex -> Integer (Wei)
                balance_wei = int(hex_balance, 16)

                # Convert Wei -> Ether (1 ETH = 10^18 Wei)
                balance_eth = balance_wei / 10**18

                print(f"{address} | {balance_eth} ETH")
            elif 'error' in response:
                print(f"{address} | RPC Error: {response['error']['message']}")

        except Exception as e:
            print(f"{address} | Error: {str(e)}")
else:
    raise ConnectionError(f"❌ Failed to connect to RPC at {rpc_url}")