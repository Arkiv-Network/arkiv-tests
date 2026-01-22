#!/usr/bin/env bash

set -e # Exit on error
set -x # Print commands

DATA_DIR="${ARKIV_SQLITE_DATA_DIRECTORY:-data}"

# Initialize Arkiv with genesis file
./geth-l2 --datadir "$DATA_DIR" init ./genesis.json

cp genesis.json ./"${DATA_DIR}"/keystore/genesis.json

echo "mysecretpassword" > data/password.txt

# 4. Import the key
grep "PRIVATE_KEY" l2/.env | cut -d'=' -f2 | sed 's/0x//' > signer.key
./geth-l2 account import --datadir data --password password.txt signer.key
rm signer.key