#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

docker compose -f "${SCRIPT_DIR}/docker-compose.yml" down --remove-orphans

echo "Sequencer stopped. Blockchain data remains in ${SCRIPT_DIR}/data."
