#!/usr/bin/env bash
#
# Execution layer (arkiv reth) for the PoS devnet. No --dev: block production
# is driven by Lighthouse over the authenticated Engine API on :8551.

set -euo pipefail

DATA_DIR=/data
GENESIS_PATH=/genesis/genesis.json

BLOCK_GAS_LIMIT="${BLOCK_GAS_LIMIT:-30000000}"
TXPOOL_MIN_PRIORITY_FEE="${TXPOOL_MIN_PRIORITY_FEE:-}"
TXPOOL_MIN_PROTOCOL_FEE="${TXPOOL_MIN_PROTOCOL_FEE:-}"

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
  --chain "$GENESIS_PATH" \
  --datadir "$DATA_DIR" \
  --builder.gaslimit "$BLOCK_GAS_LIMIT" \
  "${FEE_ARGS[@]}" \
  --http --http.addr 0.0.0.0 --http.port 8545 \
  --http.api "admin,debug,eth,txpool,net,web3,rpc,reth" \
  --ws --ws.addr 0.0.0.0 --ws.port 8546 --ws.origins "*" \
  --authrpc.addr 0.0.0.0 --authrpc.port 8551 --authrpc.jwtsecret /jwt/jwtsecret \
  --disable-discovery --no-persist-peers \
  --metrics 0.0.0.0:6160
