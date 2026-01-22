import os
import sys
import json
from eth_account import Account

# This template matches the specific configuration you requested.
# Using 'True' (Python boolean) for JSON 'true'.
GENESIS_TEMPLATE = {
    "config": {
        "chainId": 12345,
        "homesteadBlock": 0,
        "eip150Block": 0,
        "eip155Block": 0,
        "eip158Block": 0,
        "byzantiumBlock": 0,
        "constantinopleBlock": 0,
        "petersburgBlock": 0,
        "istanbulBlock": 0,
        "berlinBlock": 0,
        "londonBlock": 0,
        "shanghaiTime": 0,
        "cancunTime": 0,
        # terminalTotalDifficulty fields removed for pure Clique
        "blobSchedule": {
            "cancun": {
                "target": 3,
                "max": 6,
                "baseFeeUpdateFraction": 3338477
            }
        },
        # Ethash removed, Clique added
        "clique": {
            "period": 1,    # Block time in seconds
            "epoch": 30000  # Number of blocks before a checkpoint
        }
    },
    "difficulty": "0x1",
    "gasLimit": "30000000",
    "alloc": {}
}

def generate_keys(count):
    """
    Generate keys and populate a full genesis.json based on the template.
    """
    out_dir = '.'
    os.makedirs(out_dir, exist_ok=True)

    keys_outfile = os.path.join(out_dir, 'keys.json')
    genesis_outfile = os.path.join(out_dir, 'genesis.json')

    # Balance: 1000 ETH in Wei
    DEFAULT_BALANCE_WEI = "1000000000000000000000"

    accounts_list = []
    # Create a deep copy of the template to avoid modifying the global variable
    genesis_data = json.loads(json.dumps(GENESIS_TEMPLATE))

    print(f"Generating {count} accounts...")

    for i in range(count):
        acct = Account.create()
        addr = acct.address.lower()
        priv = acct.key.hex()

        # 1. Entry for keys.json
        accounts_list.append({
            "address": addr,
            "privateKey": priv
        })

        # 2. Entry for genesis.json alloc
        genesis_data["alloc"][addr] = {
            "balance": DEFAULT_BALANCE_WEI
        }
        if i == 0:
            with open(os.path.join("l2", ".env"), 'a') as f:
                f.write(f"\nPRIVATE_KEY=0x{priv}\n")
                f.write(f"MAIN_ACCOUNT={addr}\n")

    # Sort accounts list by address
    accounts_list.sort(key=lambda x: x['address'])

    # Sort the alloc keys in genesis for neatness
    sorted_alloc = {k: genesis_data["alloc"][k] for k in sorted(genesis_data["alloc"])}
    genesis_data["alloc"] = sorted_alloc

    # --- Write keys.json ---
    with open(keys_outfile, 'w') as f:
        json.dump(accounts_list, f, indent=4)
    print(f"Saved private keys to: {keys_outfile}")

    # --- Write genesis.json ---
    with open(genesis_outfile, 'w') as f:
        json.dump(genesis_data, f, indent=4)
    print(f"Saved genesis file to: {genesis_outfile}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python keys.py <number_of_keys>')
        sys.exit(1)

    try:
        count = int(sys.argv[1])
        if count <= 0:
            raise ValueError('Number must be positive')
        generate_keys(count)
    except ValueError as e:
        print(f'Error: Invalid number - {e}')
        sys.exit(1)