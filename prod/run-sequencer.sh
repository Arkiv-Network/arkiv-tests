#!/usr/bin/env bash

set -euo pipefail

DATA_DIR="${ARKIV_RETH_DATA_DIR:-/var/lib/arkiv-reth}"
GENESIS_PATH="${ARKIV_RETH_GENESIS_PATH:-/genesis/genesis.json}"
RPC_ADDR="${ARKIV_RETH_RPC_ADDR:-0.0.0.0}"
RPC_PORT="${ARKIV_RETH_RPC_PORT:-8545}"
WS_ADDR="${ARKIV_RETH_WS_ADDR:-0.0.0.0}"
WS_PORT="${ARKIV_RETH_WS_PORT:-8546}"
METRICS_ADDR="${ARKIV_RETH_METRICS_ADDR:-127.0.0.1:6160}"
BLOCK_TIME_SECONDS="${BLOCK_TIME_SECONDS:-2}"
BLOCK_GAS_LIMIT="${BLOCK_GAS_LIMIT:-30000000}"
# Optional fee controls (wei). Leave empty to use reth defaults.
# Change either, then re-create the sequencer to apply (chain is preserved).
TXPOOL_MIN_PRIORITY_FEE="${TXPOOL_MIN_PRIORITY_FEE:-}"
TXPOOL_MIN_PROTOCOL_FEE="${TXPOOL_MIN_PROTOCOL_FEE:-}"

if [ -z "${DEV_MNEMONIC:-}" ]; then
  echo "Missing DEV_MNEMONIC."
  echo "Set DEV_MNEMONIC in prod/.env before starting the sequencer."
  exit 1
fi

if [ ! -f "$GENESIS_PATH" ]; then
  echo "Missing genesis file: $GENESIS_PATH"
  echo "Run generate_genesis.sh before start.sh."
  exit 1
fi

if [ ! -d "$DATA_DIR" ] || [ -z "$(find "$DATA_DIR" -mindepth 1 -maxdepth 1 2>/dev/null)" ]; then
  arkiv-node init --datadir "$DATA_DIR" --chain "$GENESIS_PATH"
else
  echo "Using existing reth datadir: $DATA_DIR"
fi

FEE_ARGS=()
if [ -n "$TXPOOL_MIN_PRIORITY_FEE" ]; then
  FEE_ARGS+=(--txpool.minimum-priority-fee "$TXPOOL_MIN_PRIORITY_FEE")
fi
if [ -n "$TXPOOL_MIN_PROTOCOL_FEE" ]; then
  FEE_ARGS+=(--txpool.minimal-protocol-fee "$TXPOOL_MIN_PROTOCOL_FEE")
fi

exec arkiv-node node \
  --dev \
  --dev.block-time="${BLOCK_TIME_SECONDS}s" \
  --dev.mnemonic="$DEV_MNEMONIC" \
  --chain="$GENESIS_PATH" \
  --datadir="$DATA_DIR" \
  "${FEE_ARGS[@]}" \
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
