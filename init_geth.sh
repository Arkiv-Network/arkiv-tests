#!/usr/bin/env bash

set -e # Exit on error
set -x # Print commands

# Initialize Geth
./geth --datadir "$DATA_DIR" init ./genesis.json