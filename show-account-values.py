import json
from web3 import Web3

# 1. Define the account data provided
with open('keys.json', 'r') as f:
    accounts = json.load(f)

# 2. Connect to the local RPC
rpc_url = "http://localhost:8545"
w3 = Web3(Web3.HTTPProvider(rpc_url))

# 3. Check connection status
if w3.is_connected():
    print(f"✅ Connected to RPC at {rpc_url}\n")
    print(f"{'Address':<45} | {'Balance (ETH)'}")
    print("-" * 65)

    # 4. Loop through accounts and fetch balance
    for acc in accounts:
        # Web3 requires checksum addresses (mixed case) to be safe
        checksum_address = w3.to_checksum_address(acc["address"])

        try:
            # Get balance in Wei
            balance_wei = w3.eth.get_balance(checksum_address)

            # Convert Wei to Ether
            balance_eth = w3.from_wei(balance_wei, 'ether')

            print(f"{checksum_address} | {balance_eth} ETH")

        except Exception as e:
            print(f"{checksum_address} | Error: {str(e)}")
else:
    raise ConnectionError(f"❌ Failed to connect to RPC at {rpc_url}")