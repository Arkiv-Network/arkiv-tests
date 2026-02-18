import json
import argparse
import sys
import os

# 1 ETH = 10^18 Wei
WEI_PER_ETH = 10**18

def load_json(file_path):
    """Loads JSON data from a file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' is not valid JSON.")
        sys.exit(1)

def save_json(file_path, data):
    """Saves JSON data to a file with pretty formatting."""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)
        print(f"Success: '{file_path}' has been updated.")
    except Exception as e:
        print(f"Error: Could not write to file. {str(e)}")
        sys.exit(1)

def patch_genesis(file_path, addresses, amount_eth):
    """
    Updates the 'alloc' section of a genesis.json file.
    """
    data = load_json(file_path)

    # Calculate balance in Wei (integer)
    # We use integers for calculation but store as strings in JSON to avoid precision loss
    balance_wei = int(amount_eth * WEI_PER_ETH)
    balance_str = str(balance_wei)

    # Ensure 'alloc' key exists
    if 'alloc' not in data:
        raise Exception("'alloc' section not found in genesis file.")

    print(f"--- Adding {len(addresses)} addresses with {amount_eth} ETH each ---")

    for address in addresses:
        # Normalize address: remove 0x prefix if present, then re-add standard 0x
        clean_addr = address.strip()

        # Simple validation
        if not clean_addr.startswith("0x"):
            clean_addr = "0x" + clean_addr

        # Update the alloc object
        # Note: Some clients prefer hex balances, but decimal strings are widely supported.
        # If your client specifically needs hex balance, use: hex(balance_wei)
        data['alloc'][clean_addr] = {
            "balance": balance_str
        }
        print(f"Added/Updated: {clean_addr}")

    save_json(file_path, data)

def main():
    with open("test-accounts.txt") as r:
        addresses = [line.strip() for line in r if line.strip()]

    patch_genesis("genesis.json", addresses, 1000)

if __name__ == "__main__":
    main()