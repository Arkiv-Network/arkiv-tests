#!/usr/bin/env bash

set -e # Exit on error
set -x # Print commands

DATA_DIR="${GETH_SQLITE_DATA_DIRECTORY:-data}"

# Initialize Geth
./geth --datadir "$DATA_DIR" init ./genesis.json