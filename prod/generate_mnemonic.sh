#!/usr/bin/env bash

set -euo pipefail

if ! command -v cast >/dev/null 2>&1; then
  echo "Missing required command: cast"
  echo "Install Foundry, then run this script again."
  exit 1
fi

cast wallet new-mnemonic

cat <<'EOF'

Copy the generated Phrase into prod/.env as:

DEV_MNEMONIC="paste phrase here"

Keep this phrase private. Anyone with it can control the sequencer account.
EOF
