#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_ENV_ARGS=()

if [ -f "${SCRIPT_DIR}/.env" ]; then
  COMPOSE_ENV_ARGS=(--env-file "${SCRIPT_DIR}/.env")
fi

docker compose "${COMPOSE_ENV_ARGS[@]}" -f "${SCRIPT_DIR}/docker-compose.yml" down --remove-orphans

echo "Sequencer stopped. Blockchain data remains in ${SCRIPT_DIR}/data."
