#!/usr/bin/env bash

set -e # Exit on error
set -x # Print commands

# Default address if not provided
ADDR="${MAIN_ACCOUNT_ADDRESS:-0x70997970C51812dc3A010C7d01b50e0d17dc79C8}"
DATA_DIR="${GETH_SQLITE_DATA_DIRECTORY:-data}"

# Use | as a delimiter to avoid confusion with address characters
# This replaces the string "MAIN_ACCOUNT" with the actual address
sed -i "s|MAIN_ACCOUNT|$ADDR|g" ./genesis.json

# Initialize Geth
./geth --datadir "$DATA_DIR" init ./genesis.json