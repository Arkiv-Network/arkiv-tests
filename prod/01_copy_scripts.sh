#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cp "${REPO_ROOT}/generate-pure-reth-genesis.py" "${SCRIPT_DIR}/generate-pure-reth-genesis.py"
cp "${REPO_ROOT}/test-accounts.txt" "${SCRIPT_DIR}/test-accounts.txt"

chmod +x "${SCRIPT_DIR}/run-sequencer.sh"
chmod +x "${SCRIPT_DIR}/generate-genesis-entrypoint.sh"
chmod +x "${SCRIPT_DIR}/start.sh"
chmod +x "${SCRIPT_DIR}/stop.sh"
chmod +x "${SCRIPT_DIR}/cleanup.sh"
chmod +x "${SCRIPT_DIR}/02_generate_genesis.sh"

echo "Copied prod runtime scripts and inputs."
