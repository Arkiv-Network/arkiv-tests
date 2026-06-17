import argparse
import sys
import time

import requests


def get_block_number(rpc_url):
    """
    Sends a JSON-RPC request to get the current block number.
    Returns the integer block number or 0 if the request fails.
    """
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1,
    }

    try:
        response = requests.post(rpc_url, json=payload, headers=headers, timeout=2)
        response.raise_for_status()
        data = response.json()

        if "result" in data and data["result"] is not None:
            return int(data["result"], 16)
    except Exception:
        return 0

    return 0


def wait_for_block_production(rpc_url, companion_rpc_url, timeout, required_blocks):
    """
    Waits for an Ethereum RPC endpoint to report block production.
    """
    print("Waiting for RPC to start producing blocks...")
    print(f"Target: {required_blocks} blocks within {timeout} seconds.")
    print(f"RPC URL: {rpc_url}")

    start_time = time.time()
    blocks_seen = 0
    blocks_advanced = -1
    last_block = -1

    while time.time() - start_time < timeout:
        block_number = get_block_number(rpc_url)
        if block_number != last_block:
            blocks_advanced += 1
            last_block = block_number

        if block_number > 0:
            print(f"RPC is live. Current block: {block_number}")

            if companion_rpc_url:
                companion_block = get_block_number(companion_rpc_url)
                print(f"Companion RPC current block: {companion_block}")

            blocks_seen += 1

            if blocks_seen >= required_blocks and blocks_advanced >= required_blocks:
                print(
                    f"RPC has produced at least {blocks_advanced} blocks. "
                    "Proceeding with the workflow."
                )
                return
        else:
            print(f"Waiting for RPC... (Current block: {block_number})")

        time.sleep(1)

    print("RPC did not start producing blocks in time.")
    sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Wait for an Ethereum RPC endpoint to start producing blocks."
    )
    parser.add_argument(
        "--l2-url",
        type=str,
        default="http://localhost:8545",
        help="The primary RPC endpoint (default: http://localhost:8545)",
    )
    parser.add_argument(
        "--l1-url",
        type=str,
        default="",
        help="Optional companion RPC endpoint to print while waiting",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Max time to wait in seconds (default: 60)",
    )
    parser.add_argument(
        "--blocks",
        type=int,
        default=5,
        help="Number of successful block checks required (default: 5)",
    )

    args = parser.parse_args()

    wait_for_block_production(
        rpc_url=args.l2_url,
        companion_rpc_url=args.l1_url,
        timeout=args.timeout,
        required_blocks=args.blocks,
    )
