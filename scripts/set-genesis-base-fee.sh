#!/usr/bin/env bash

set -euo pipefail

GENESIS_FILE="${1:-genesis.json}"
MIN_BASE_FEE_WEI=10000000
MIN_BASE_FEE_HEX=$(printf "0x%x" "$MIN_BASE_FEE_WEI")

if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq is required to set genesis baseFeePerGas." >&2
    exit 1
fi

if [ ! -f "$GENESIS_FILE" ]; then
    echo "Error: $GENESIS_FILE not found." >&2
    exit 1
fi

tmp_file="${GENESIS_FILE}.tmp"
jq --arg base_fee "$MIN_BASE_FEE_HEX" '.baseFeePerGas = $base_fee' "$GENESIS_FILE" > "$tmp_file"
mv "$tmp_file" "$GENESIS_FILE"

echo "Set ${GENESIS_FILE} baseFeePerGas to ${MIN_BASE_FEE_HEX} (${MIN_BASE_FEE_WEI} wei, 0.01 Gwei)."
