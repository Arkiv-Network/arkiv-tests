import os
import sys
import json
from eth_account import Account

# This template matches the specific configuration you requested.
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
    # extraData will be dynamically populated in generate_keys
}

def generate_keys(count):
    """
    Generate keys and populate a full genesis.json based on the template.
    Automatically configures the first account as the Clique Signer.
    """
    out_dir = '.'
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs("l2", exist_ok=True) # Ensure l2 dir exists for .env

    keys_outfile = os.path.join(out_dir, 'keys.json')
    genesis_outfile = os.path.join(out_dir, 'genesis.json')

    # Balance: 1000 ETH in Wei
    DEFAULT_BALANCE_WEI = "1000000000000000000000"

    accounts_list = []
    # Create a deep copy of the template to avoid modifying the global variable
    genesis_data = json.loads(json.dumps(GENESIS_TEMPLATE))

    signer_address = None

    print(f"Generating {count} accounts...")

    for i in range(count):
        acct = Account.create()
        addr = acct.address.lower()
        # Remove '0x' from private key for clean usage, or keep it if preferred.
        # Usually tools prefer raw hex without prefix for keys.json, but with 0x for .env
        priv_hex = acct.key.hex()

        # Capture the first address to be the Clique Signer
        if i == 0:
            signer_address = addr
            # Overwrite/Create .env file
            with open(os.path.join("l2", ".env"), 'w') as f:
                f.write(f"PRIVATE_KEY={priv_hex}\n")
                f.write(f"MAIN_ACCOUNT={addr}\n")

        # 1. Entry for keys.json
        accounts_list.append({
            "address": addr,
            "privateKey": priv_hex
        })

        # 2. Entry for genesis.json alloc
        genesis_data["alloc"][addr] = {
            "balance": DEFAULT_BALANCE_WEI
        }

    # --- CRITICAL FIX: Generate Clique extraData ---
    if signer_address:
        # Clique extraData format:
        # 1. Vanity (32 bytes / 64 hex chars)
        # 2. Signer Address (20 bytes / 40 hex chars)
        # 3. Seal (65 bytes / 130 hex chars) - Must be 0s for genesis

        vanity = "0" * 64
        signer = signer_address.replace("0x", "")
        seal = "0" * 130

        genesis_data["extraData"] = f"0x{vanity}{signer}{seal}"
        print(f"Set Clique Signer to: {signer_address}")
    else:
        print("Error: No signer address generated.")
        return

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