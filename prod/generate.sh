#!/usr/bin/env bash
#
# Generate EL + CL genesis, JWT and the single validator keystore for the Arkiv
# PoS devnet. Re-run this whenever you want a fresh chain: it stamps the genesis
# with the current time so the beacon chain starts at "now + delay".

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

GEN_TAG="${GEN_TAG:-6.1.0}"

if [ -x ../.venv/Scripts/python.exe ]; then
  PYTHON_BIN="${PYTHON_BIN:-../.venv/Scripts/python.exe}"
elif [ -x ../.venv/bin/python ]; then
  PYTHON_BIN="${PYTHON_BIN:-../.venv/bin/python}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

for required_var in OPERATOR_PRIVATE_KEY OPERATOR_ADDRESS VALIDATOR_PRIVATE_KEY VALIDATOR_ADDRESS; do
  if [ -z "${!required_var:-}" ]; then
    echo "Missing $required_var. Run ./generate-env.sh or set it in .env." >&2
    exit 1
  fi
done

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
echo "CL_ADDITIONAL_VALIDATORS=additional-validators.txt" >> "$RUNTIME_VALUES"
if [ -n "${TEST_ACCOUNTS_MNEMONIC:-}" ]; then
  echo "EL_AND_CL_MNEMONIC=\"${TEST_ACCOUNTS_MNEMONIC}\"" >> "$RUNTIME_VALUES"
fi

"$PYTHON_BIN" prod_keys.py genesis-validator --out config/additional-validators.txt

if WIN_DIR="$(pwd -W 2>/dev/null)"; then
  :
else
  WIN_DIR="$(pwd)"
fi

# 1) EL + CL genesis, JWT.
rm -rf output && mkdir -p output
docker run --rm \
  -v "${WIN_DIR}/output:/data" \
  -v "${WIN_DIR}/${RUNTIME_VALUES}:/config/values.env" \
  -v "${WIN_DIR}/config/cl/mnemonics.yaml:/config/cl/mnemonics.yaml" \
  -v "${WIN_DIR}/config/additional-validators.txt:/config/additional-validators.txt" \
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
"$PYTHON_BIN" prod_keys.py keystore --out-dir validators

echo "Genesis + keys generated. CL genesis_time=$((GEN_TS + 20)) (now + GENESIS_DELAY)."
echo "Bring the stack up promptly:  docker compose up -d"
