#!/usr/bin/env bash

set -euo pipefail

python generate-pure-reth-genesis.py
arkiv-cli inject-predeploy "${PURE_RETH_GENESIS_PATH:-/genesis/genesis.json}"
