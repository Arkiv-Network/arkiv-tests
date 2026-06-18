#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
GENESIS_PATH="${SCRIPT_DIR}/genesis/genesis.json"

if [ ! -f "$GENESIS_PATH" ]; then
  echo "Missing genesis file: $GENESIS_PATH"
  echo "Run 02_generate_genesis.sh before start.sh."
  exit 1
fi

mkdir -p "${SCRIPT_DIR}/data"

docker compose -f "${SCRIPT_DIR}/docker-compose.yml" up -d --build --force-recreate sequencer

echo "Sequencer started."
echo "RPC:     http://127.0.0.1:${RPC_PORT:-8545}"
echo "WS:      ws://127.0.0.1:${WS_PORT:-8546}"
echo "Metrics: http://127.0.0.1:${METRICS_PORT:-6160}"
