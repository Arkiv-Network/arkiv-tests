#!/usr/bin/env bash

set -e # Exit on error
set -x # Print commands

DATA_DIR="${ARKIV_SQLITE_DATA_DIRECTORY:-data}"

# Initialize Arkiv with genesis file
./arkiv --datadir "$DATA_DIR" init ./genesis.json

cp genesis.json ./"${DATA_DIR}"/keystore/genesis.json
