#!/usr/bin/env bash

set -euo pipefail

RPC_URL="${RPC_URL:-http://127.0.0.1:${RPC_PORT:-8545}}"

rpc_call() {
  local payload="$1"
  curl -fsS \
    -H "Content-Type: application/json" \
    --data "$payload" \
    "$RPC_URL"
}

BLOCK_NUMBER_HEX="$(rpc_call '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' | python -c 'import json, sys; print(json.load(sys.stdin)["result"])')"
export BLOCK_JSON
BLOCK_JSON="$(rpc_call "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBlockByNumber\",\"params\":[\"${BLOCK_NUMBER_HEX}\",false],\"id\":2}")"

python - "$BLOCK_NUMBER_HEX" <<'PY'
import datetime
import json
import os
import sys

block_number_hex = sys.argv[1]
response = json.loads(os.environ["BLOCK_JSON"])
block = response["result"]

block_number = int(block_number_hex, 16)
timestamp = int(block["timestamp"], 16)
block_date = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)

print(f"RPC: {block_number_hex} ({block_number})")
print(f"Latest block date: {block_date.isoformat()}")
PY
