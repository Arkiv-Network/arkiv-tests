#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -x ../.venv/Scripts/python.exe ]; then
  PYTHON_BIN="${PYTHON_BIN:-../.venv/Scripts/python.exe}"
elif [ -x ../.venv/bin/python ]; then
  PYTHON_BIN="${PYTHON_BIN:-../.venv/bin/python}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

"$PYTHON_BIN" prod_keys.py env --out .env

echo "Wrote .env with OPERATOR_PRIVATE_KEY, OPERATOR_ADDRESS, VALIDATOR_PRIVATE_KEY and VALIDATOR_ADDRESS."
echo "Store it securely. The private keys are not committed."
