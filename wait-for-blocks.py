import time
import sys
import requests
import argparse

def get_block_number(rpc_url):
    """
    Sends a JSON-RPC request to get the current block number.
    Returns the integer block number or 0 if the request fails.
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1
    }

    try:
        response = requests.post(rpc_url, json=payload, headers=headers, timeout=2)
        response.raise_for_status()
        data = response.json()

        # Eth RPC returns block numbers in Hex (e.g., "0x1a"), convert to int
        if 'result' in data and data['result'] is not None:
            return int(data['result'], 16)
    except Exception:
        # If connection fails or data is bad, return 0 (equivalent to Bash 2>/dev/null)
        return 0

def wait_for_l2_production(l2_url, l1_url, timeout, required_blocks):
    """
    Waits for the L2 node to report a block number > 0 for a specific number of checks.
    """
    print(f"Waiting for L2 to start producing blocks...")
    print(f"Target: {required_blocks} blocks within {timeout} seconds.")
    print(f"L2 URL: {l2_url}")

    start_time = time.time()
    blocks_seen = 0

    while time.time() - start_time < timeout:
        # 1. Get L2 Block
        l2_block = get_block_number(l2_url)

        # 2. Check if block is valid and > 0
        if l2_block > 0:
            print(f"✅ L2 is live! Current block: {l2_block}")

            # 3. Get L1 Status (Optional, but included for parity with original script)
            if l1_url:
                l1_block = get_block_number(l1_url)
                print(f"✅ L1 Current block: {l1_block}")

            # Increment success counter
            blocks_seen += 1

            # Check exit condition
            if blocks_seen >= required_blocks:
                print(f"L2 has produced {blocks_seen} blocks. Proceeding with the workflow.")
                return # Success

        else:
            print(f"Waiting for L2... (Current block: {l2_block})")

        # Sleep before next check
        time.sleep(1)

    # If loop finishes without returning, we failed
    print("❌ L2 did not start producing blocks in time.")
    sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wait for L2 RPC to start producing blocks.")

    # Argument: L2 RPC URL
    parser.add_argument(
        "--l2-url",
        type=str,
        default="http://localhost:8545",
        help="The RPC endpoint for the L2 node (default: http://localhost:8545)"
    )

    # Argument: L1 RPC URL
    parser.add_argument(
        "--l1-url",
        type=str,
        default="http://localhost:15900",
        help="The RPC endpoint for the L1 node (default: http://localhost:15900)"
    )

    # Argument: Timeout
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Max time to wait in seconds (default: 60)"
    )

    # Argument: Block Count
    parser.add_argument(
        "--blocks",
        type=int,
        default=5,
        help="Number of successful block checks required (default: 5)"
    )

    args = parser.parse_args()

    wait_for_l2_production(
        l2_url=args.l2_url,
        l1_url=args.l1_url,
        timeout=args.timeout,
        required_blocks=args.blocks
    )