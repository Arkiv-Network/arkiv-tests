#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
GENESIS_DIR="${SCRIPT_DIR}/genesis"
GENESIS_PATH="${GENESIS_DIR}/genesis.json"
DATA_DIR="${SCRIPT_DIR}/data"

if [ -f "$GENESIS_PATH" ]; then
  echo "Genesis already exists: $GENESIS_PATH"
  echo "Refusing to overwrite it."
  exit 1
fi

if [ -d "$DATA_DIR" ] && [ -n "$(find "$DATA_DIR" -mindepth 1 -maxdepth 1 2>/dev/null)" ]; then
  echo "Blockchain data already exists: $DATA_DIR"
  echo "Refusing to generate a new genesis for existing chain data."
  exit 1
fi

mkdir -p "$GENESIS_DIR" "$DATA_DIR"

docker compose -f "${SCRIPT_DIR}/docker-compose.yml" build sequencer
docker compose -f "${SCRIPT_DIR}/docker-compose.yml" run --rm genesis-generator

echo "Generated genesis: $GENESIS_PATH"
