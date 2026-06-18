#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

echo "This will stop the prod sequencer and remove local prod chain state."
echo "Data directory: ${SCRIPT_DIR}/data"
echo "Genesis file:   ${SCRIPT_DIR}/genesis/genesis.json"
read -r -p "Press y to confirm cleanup: " CONFIRM

if [ "$CONFIRM" != "y" ]; then
  echo "Cleanup cancelled."
  exit 0
fi

docker compose -f "${SCRIPT_DIR}/docker-compose.yml" down --remove-orphans
rm -rf "${SCRIPT_DIR}/data" "${SCRIPT_DIR}/genesis"

echo "Cleanup complete."
