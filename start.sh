#!/usr/bin/env bash

set -euo pipefail

DATA_DIR="${ARKIV_RETH_DATA_DIR:-sequencer-data}"
RPC_ADDR="${ARKIV_RETH_RPC_ADDR:-0.0.0.0}"
RPC_PORT="${ARKIV_RETH_RPC_PORT:-8545}"
WS_ADDR="${ARKIV_RETH_WS_ADDR:-0.0.0.0}"
WS_PORT="${ARKIV_RETH_WS_PORT:-8546}"
METRICS_ADDR="${ARKIV_RETH_METRICS_ADDR:-127.0.0.1:6160}"
CHAIN_ID="${CHAIN_ID:-42069}"
BLOCK_TIME_SECONDS="${BLOCK_TIME_SECONDS:-2}"
BLOCK_GAS_LIMIT="${BLOCK_GAS_LIMIT:-30000000}"
DEV_MNEMONIC="${DEV_MNEMONIC:-parent picture garment parrot churn record stadium pill rocket craft fish fiscal clip virus view diary replace wealth extra kitten door enforce piece nut}"

export PURE_RETH_CHAIN_ID="$CHAIN_ID"
export PURE_RETH_BLOCK_TIME_SECONDS="$BLOCK_TIME_SECONDS"
export PURE_RETH_GAS_LIMIT="$BLOCK_GAS_LIMIT"

python generate-pure-reth-genesis.py
arkiv-cli inject-predeploy genesis.json

if [ ! -d "$DATA_DIR" ] || [ -z "$(find "$DATA_DIR" -mindepth 1 -maxdepth 1 2>/dev/null)" ]; then
  arkiv-node init --datadir "$DATA_DIR" --chain genesis.json
else
  echo "Using existing reth datadir: $DATA_DIR"
fi

exec arkiv-node node \
  --dev \
  --dev.block-time="${BLOCK_TIME_SECONDS}s" \
  --dev.mnemonic="$DEV_MNEMONIC" \
  --chain=genesis.json \
  --datadir="$DATA_DIR" \
  --http \
  --http.addr="$RPC_ADDR" \
  --http.port="$RPC_PORT" \
  --http.api="admin,debug,eth,txpool,net,web3,rpc,reth,miner" \
  --ws \
  --ws.addr="$WS_ADDR" \
  --ws.port="$WS_PORT" \
  --ws.api="admin,debug,eth,txpool,net,web3,rpc,reth,miner" \
  --ws.origins="*" \
  --disable-auth-server \
  --disable-discovery \
  --no-persist-peers \
  --builder.gaslimit="$BLOCK_GAS_LIMIT" \
  --metrics "$METRICS_ADDR"
