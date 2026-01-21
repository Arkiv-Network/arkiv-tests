#!/usr/bin/env bash

set -e # Exit on error
set -x # Print commands

DATA_DIR = "${GETH_SQLITE_DATA_DIRECTORY:-data}"

# Default address if not provided
ADDR="${MAIN_ACCOUNT_ADDRESS:-0x70997970C51812dc3A010C7d01b50e0d17dc79C8}"

# Show balance of the main account
curl -X POST --data '{"jsonrpc":"2.0","method":"eth_getBalance","params":["'"$ADDR"'", "latest"],"id":1}' -H "Content-Type: application/json" http://localhost:8545