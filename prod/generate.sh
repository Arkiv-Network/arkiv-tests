#!/usr/bin/env bash
#
# Generate EL + CL genesis, JWT and the single validator keystore for the
# Arkiv PoS devnet. Re-run this whenever you want a fresh chain: it stamps the
# genesis with the current time so the beacon chain starts at "now + delay".

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GEN_TAG="${GEN_TAG:-6.1.0}"
VALTOOLS_TAG="${VALTOOLS_TAG:-latest}"
MNEMONIC="${EL_AND_CL_MNEMONIC:-style insect tray body company scan annual rebuild rely crazy patient anger}"

# Stamp genesis at the current time so the CL genesis_time is sane.
# The generator maps GENESIS_TIMESTAMP -> config.yaml MIN_GENESIS_TIME.
GEN_TS="$(date +%s)"
echo "Stamping genesis GENESIS_TIMESTAMP=${GEN_TS}"

# Build the effective values file = committed config/values.env + fresh
# timestamp. Keep it inside the repo so Docker can bind-mount it on Windows
# (a /tmp mktemp path does not bind-mount under MSYS_NO_PATHCONV=1).
mkdir -p config
RUNTIME_VALUES="config/values.runtime.env"
cat config/values.env > "$RUNTIME_VALUES"
echo "GENESIS_TIMESTAMP=${GEN_TS}" >> "$RUNTIME_VALUES"

WIN_DIR="$(pwd -W)"

# 1) EL + CL genesis, JWT.
rm -rf output && mkdir -p output
docker run --rm \
  -v "${WIN_DIR}/output:/data" \
  -v "${WIN_DIR}/${RUNTIME_VALUES}:/config/values.env" \
  "ethpandaops/ethereum-genesis-generator:${GEN_TAG}" all

# 2) Lighthouse testnet-dir.
rm -rf testnet && mkdir -p testnet
cp output/metadata/config.yaml output/metadata/genesis.ssz testnet/
# Lighthouse expects deposit_contract_block.txt; older tooling used deploy_block.txt.
cp output/metadata/deposit_contract_block.txt testnet/deposit_contract_block.txt
cp output/metadata/deposit_contract_block.txt testnet/deploy_block.txt
printf '[]\n' > testnet/boot_enr.yaml

# 3) Single validator keystore (lighthouse layout under validators/gen/{keys,secrets}).
rm -rf validators && mkdir -p validators
docker run --rm \
  -v "${WIN_DIR}/validators:/out" \
  "protolambda/eth2-val-tools:${VALTOOLS_TAG}" keystores \
  --insecure \
  --out-loc /out/gen \
  --source-mnemonic "$MNEMONIC" \
  --source-min 0 --source-max 1

echo "Genesis + keys generated. CL genesis_time=$((GEN_TS + 20)) (now + GENESIS_DELAY)."
echo "Bring the stack up promptly:  docker compose up -d"
