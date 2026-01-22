import os
import subprocess
import sys
import json

# --- OP STACK CONFIGURATION ---
GENESIS_TEMPLATE = {
    "config": {
        "chainId": 42069, # Standard Devnet ID
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
        "arrowGlacierBlock": 0,
        "grayGlacierBlock": 0,
        "mergeNetsplitBlock": 0,

        # OP Stack Specific Hardforks (Set to 0 for instant activation)
        "bedrockBlock": 0,
        "regolithBlock": 0,
        "canyonBlock": 0,
        "deltaBlock": 0,
        "ecotoneBlock": 0,

        "terminalTotalDifficulty": 0,
        "terminalTotalDifficultyPassed": True,

        # Critical for op-geth to behave as L2
        "optimism": {
            "eip1559Elasticity": 6,
            "eip1559Denominator": 50
        }
    },
    "nonce": "0x0",
    "timestamp": "0x0",
    "extraData": "0x",
    "gasLimit": "0x1C9C380", # 30,000,000 in Hex
    "difficulty": "0x0",      # Must be 0 for PoS/OP Stack
    "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "coinbase": "0x0000000000000000000000000000000000000000",
    "alloc": {}
}

def generate_keys(count):
    out_dir = '.'
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs("l2-data", exist_ok=True)

    keys_outfile = os.path.join(out_dir, 'dev_keys.json')
    genesis_outfile = os.path.join(out_dir, 'genesis.json')
    jwt_outfile = os.path.join(out_dir, 'jwt.txt')

    # Balance: 1000 ETH
    DEFAULT_BALANCE_WEI = "0x3635C9ADC5DEA00000"

    accounts_list = []
    genesis_data = json.loads(json.dumps(GENESIS_TEMPLATE))

    print(f"Generating {count} accounts...")

    # 1. Generate JWT Secret (Needed for Engine API)
    with open(jwt_outfile, 'w') as f:
        # Just a random hex string for dev
        f.write("0000000000000000000000000000000000000000000000000000000000000000")
    print(f"Created dummy JWT at {jwt_outfile}")

    for i in range(count):
        result = subprocess.run(
            ["cast", "wallet", "new", "--json"],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the JSON output (cast returns a list of wallets)
        wallet_data = json.loads(result.stdout)[0]

        # Extract variables matching your original format
        addr = wallet_data["address"].lower()
        priv_hex = wallet_data["private_key"] # cast output already includes '0x'

        # Save first account as the "Sequencer"
        if i == 0:
            with open(os.path.join("l2-data", ".env"), 'w') as f:
                f.write(f"SEQUENCER_PRIVATE_KEY={priv_hex}\n")
                f.write(f"SEQUENCER_ADDRESS={addr}\n")

        accounts_list.append({
            "address": addr,
            "privateKey": priv_hex
        })

        genesis_data["alloc"][addr] = {
            "balance": DEFAULT_BALANCE_WEI
        }

    # IMPORTANT:
    # In a real OP Stack chain, we would need to inject the
    # 'Predeploy' contracts here (Key addresses starting with 0x4200...)
    # Without them, op-node will likely panic.

    # Write files
    with open(keys_outfile, 'w') as f:
        json.dump(accounts_list, f, indent=4)

    with open(genesis_outfile, 'w') as f:
        json.dump(genesis_data, f, indent=4)

    print(f"Success. Genesis saved to {genesis_outfile}")
    print(f"WARNING: This genesis lacks OP Stack system contracts (Predeploys).")
    print(f"op-geth will start, but op-node will likely fail to derive blocks.")

if __name__ == '__main__':
    try:
        # Default to 10 keys if no arg
        count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
        generate_keys(count)
    except Exception as e:
        print(f"Error: {e}")