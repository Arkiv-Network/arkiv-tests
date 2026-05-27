#!/usr/bin/env bash

set -euo pipefail

BATCHER_RPC_HOST="${BATCHER_RPC_HOST:-0.0.0.0}"
BATCHER_RPC_PORT="${BATCHER_RPC_PORT:-8548}"
COLLECTOR_LISTEN_HOST="${COLLECTOR_LISTEN_HOST:-0.0.0.0}"
COLLECTOR_LISTEN_PORT="${COLLECTOR_LISTEN_PORT:-28881}"
COLLECTOR_HISTORY_SIZE="${HISTORY_SIZE:-5000}"
COLLECTOR_BATCHER_RPC_URL="${BATCHER_RPC_URL:-http://127.0.0.1:${BATCHER_RPC_PORT}}"

read_deploy_key() {
  local key_name="$1"
  awk -F= -v key="$key_name" '$1 == key {print substr($0, length(key) + 2); exit}' deploy-config/keys.txt
}

wait_for_rpc() {
  local name="$1"
  local url="$2"
  local method="$3"
  local max_retries="$4"
  local counter=0

  while [ "$counter" -lt "$max_retries" ]; do
    if curl -fsS \
      -H "Content-Type: application/json" \
      --data "{\"jsonrpc\":\"2.0\",\"method\":\"${method}\",\"params\":[],\"id\":1}" \
      "$url" > /dev/null; then
      echo "$name RPC is ready at $url"
      return 0
    fi

    counter=$((counter+1))
    echo "Waiting for $name RPC... ${counter}/${max_retries}"
    sleep 1
  done

  echo "Error: $name RPC did not become available at $url within ${max_retries} seconds."
  return 1
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local max_retries="$3"
  local counter=0

  while [ "$counter" -lt "$max_retries" ]; do
    if curl -fsS "$url" > /dev/null; then
      echo "$name HTTP API is ready at $url"
      return 0
    fi

    counter=$((counter+1))
    echo "Waiting for $name HTTP API... ${counter}/${max_retries}"
    sleep 1
  done

  echo "Error: $name HTTP API did not become available at $url within ${max_retries} seconds."
  return 1
}

# Get current timestamp in hex
NOW_HEX=$(printf "0x%x" "$(date +%s)")
# Replace timestamp in anvil-chain.json (requires jq)
jq --arg t "$NOW_HEX" '.timestamp = $t' anvil-chain.json > anvil-chain.tmp && mv anvil-chain.tmp anvil-chain.json
echo "Updated Genesis timestamp to: $NOW_HEX"

anvil --init anvil-chain.json -p 15900 --block-time 1 > anvil.log 2>&1 &

# Initialize the deployment intent
op-deployer init --l1-chain-id 31337 --l2-chain-ids 42069 --workdir deploy-config --intent-type custom
python generate-intent.py
op-deployer apply --l1-rpc-url http://localhost:15900 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --workdir deploy-config
op-deployer inspect genesis --workdir deploy-config 42069 > genesis.json
op-deployer inspect rollup --workdir deploy-config 42069 > rollup.json

# Fund test accounts and pin the L2 genesis baseFeePerGas to 0.01 Gwei (matches Jovian minBaseFee).
python patch-genesis.py

op-geth --datadir ./l2-data init genesis.json
openssl rand -hex 32 > jwt.txt

echo "Starting L2 node op-geth..."
op-geth \
  --datadir ./l2-data \
  --http \
  --http.port 8545 \
  --http.addr "0.0.0.0" \
  --http.vhosts "*" \
  --http.api "eth,net,engine,web3,debug,trace" \
  --authrpc.addr "localhost" \
  --authrpc.port 8551 \
  --authrpc.vhosts "*" \
  --authrpc.jwtsecret jwt.txt \
  --syncmode=full \
  --gcmode=archive \
  --nodiscover \
  --networkid=42069 \
  > op-geth.log 2>&1 &

echo "Starting L2 node op-node..."
op-node \
  --l2=http://localhost:8551 \
  --l2.jwt-secret=jwt.txt \
  --sequencer.enabled \
  --sequencer.l1-confs=0 \
  --verifier.l1-confs=0 \
  --rpc.addr=0.0.0.0 \
  --rpc.port=8547 \
  --p2p.disable \
  --l1=http://localhost:15900 \
  --l1.rpckind=basic \
  --rollup.config=rollup.json \
  --rollup.l1-chain-config anvil-chain.json \
  --p2p.sequencer.key=ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  --l1.beacon.ignore \
  > op-node.log 2>&1 &

# Wait up to 60 seconds for L2 to produce blocks.
echo "Waiting for L2 to start producing blocks..."
end=$((SECONDS+60))
NUM_BLOCKS=0
LAST_L2_BLOCK=0

while [ $SECONDS -lt $end ]; do
  # Try to get the block number, suppress error output
  L2_BLOCK=$(cast block-number --rpc-url http://localhost:8545 2>/dev/null || echo "0")

  # Check if block number is a valid integer and greater than 0
  if [[ "$L2_BLOCK" =~ ^[0-9]+$ ]] && [ "$L2_BLOCK" -gt 0 ]; then
    echo "L2 is live! Current block: $L2_BLOCK"

    # Print L1 status as well for confirmation
    L1_BLOCK=$(cast block-number --rpc-url http://localhost:15900 2>/dev/null || echo "unknown")
    echo "L1 Current block: $L1_BLOCK"

    if [ "$L2_BLOCK" -gt "$LAST_L2_BLOCK" ]; then
      NUM_BLOCKS=$((NUM_BLOCKS+1))
      LAST_L2_BLOCK="$L2_BLOCK"
    fi

    if [ "$NUM_BLOCKS" -ge 3 ]; then
      break
    fi

    sleep 1
    continue
  fi

  echo "Waiting for L2... (Current block: $L2_BLOCK)"
  sleep 1
done

if [ "$NUM_BLOCKS" -lt 3 ]; then
  echo "Error: L2 did not produce enough blocks within 60 seconds."
  exit 1
fi

BATCHER_PRIVATE_KEY="${BATCHER_PRIVATE_KEY:-$(read_deploy_key BATCHER_PRIVATE_KEY)}"
if [ -z "$BATCHER_PRIVATE_KEY" ]; then
  echo "Error: BATCHER_PRIVATE_KEY is missing from the environment and deploy-config/keys.txt."
  exit 1
fi

echo "Starting op-batcher..."
op-batcher \
  --l1-eth-rpc=http://localhost:15900 \
  --l2-eth-rpc=http://localhost:8545 \
  --rollup-rpc=http://localhost:8547 \
  --private-key="$BATCHER_PRIVATE_KEY" \
  --poll-interval="${OP_BATCHER_POLL_INTERVAL:-1s}" \
  --sub-safety-margin="${OP_BATCHER_SUB_SAFETY_MARGIN:-6}" \
  --num-confirmations="${OP_BATCHER_NUM_CONFIRMATIONS:-1}" \
  --safe-abort-nonce-too-low-count="${OP_BATCHER_SAFE_ABORT_NONCE_TOO_LOW_COUNT:-3}" \
  --resubmission-timeout="${OP_BATCHER_RESUBMISSION_TIMEOUT:-30s}" \
  --max-channel-duration="${OP_BATCHER_MAX_CHANNEL_DURATION:-1}" \
  --rpc.addr="$BATCHER_RPC_HOST" \
  --rpc.port="$BATCHER_RPC_PORT" \
  --rpc.enable-admin \
  > op-batcher.log 2>&1 &

wait_for_rpc "op-batcher" "http://127.0.0.1:${BATCHER_RPC_PORT}" "admin_getThrottleController" 30

echo "Starting op-batcher-collector..."
env \
  BATCHER_RPC_URL="$COLLECTOR_BATCHER_RPC_URL" \
  HISTORY_SIZE="$COLLECTOR_HISTORY_SIZE" \
  COLLECTOR_LISTEN_HOST="$COLLECTOR_LISTEN_HOST" \
  COLLECTOR_LISTEN_PORT="$COLLECTOR_LISTEN_PORT" \
  op-batcher-collector \
  > op-batcher-collector.log 2>&1 &

wait_for_http "op-batcher-collector" "http://127.0.0.1:${COLLECTOR_LISTEN_PORT}/health" 30

echo "op-batcher-collector API for arkiv-chain-indexer: http://127.0.0.1:${COLLECTOR_LISTEN_PORT}"
wait -n
