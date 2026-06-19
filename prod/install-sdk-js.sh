#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

ARKIV_SDK_JS_REF="${ARKIV_SDK_JS_REF:-codex/fix-byte-aligned-numeric-attributes}"
SDK_DIR="${REPO_DIR}/arkiv-sdk-js"

rm -rf "$SDK_DIR"
git clone https://github.com/Arkiv-Network/arkiv-sdk-js "$SDK_DIR"
(
  cd "$SDK_DIR"
  git checkout "$ARKIV_SDK_JS_REF"
  bun install
  bun run package:test
  ls -lha arkiv-network-sdk-latest.tgz
)

cd "$REPO_DIR"
bun install

echo "Installed @arkiv-network/sdk from arkiv-sdk-js ref: ${ARKIV_SDK_JS_REF}"
