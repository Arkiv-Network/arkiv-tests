# Get current timestamp in hex
NOW_HEX=$(printf "0x%x" $(date +%s))
# Replace timestamp in anvil-chain.json (requires jq)
jq --arg t "$NOW_HEX" '.timestamp = $t' anvil-chain.json > anvil-chain.tmp && mv anvil-chain.tmp anvil-chain.json
echo "Updated Genesis timestamp to: $NOW_HEX"

anvil --init anvil-chain.json -p 15900 --block-time 1 > anvil.log 2>&1 &
# Initialize the deployment intent
op-deployer init --l1-chain-id 31337 --l2-chain-ids 42069 --workdir deploy-config --intent-type custom
python generate-intent-arkiv.py
echo "Contents of deploy-config/intent.toml:\n" && cat deploy-config/intent.toml
op-deployer apply --l1-rpc-url http://localhost:15900 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --workdir deploy-config
op-deployer inspect genesis --workdir deploy-config 42069 > genesis.json
op-deployer inspect rollup --workdir deploy-config 42069 > rollup.json

python patch-genesis.py

op-geth --datadir ./l2-data init --state.scheme=hash genesis.json > init_output.txt 2>&1

# 3. Use 'console' mode to query the database for the exact block hash
# We use --exec to run a distinct JavaScript command
echo "Querying database for full hash..."
FULL_HASH=$(op-geth --datadir l2-data --verbosity 0 console --exec "eth.getBlock(0).hash")

# Clean up quotes from the output (e.g., "0x..." -> 0x...)
FULL_HASH=$(echo "$FULL_HASH" | tr -d '"')

# Validate the hash length (should be 66 characters: 0x + 64 hex chars)
if [[ ${#FULL_HASH} -ne 66 ]]; then
  echo "Error: Retrieved invalid hash: $FULL_HASH"
  exit 1
fi

echo "Detected Full Genesis Hash: $FULL_HASH"

# 4. Update rollup.json
# - Sets .genesis.l2.hash to the new hash
# - Deletes the invalid .l2_genesis block at the bottom
echo "Patching rollup.json..."
jq --arg hash "$FULL_HASH" '
  .genesis.l2.hash = $hash |
  del(.l2_genesis)
  ' "rollup.json" > "rollup.json.tmp" && mv "rollup.json.tmp" "rollup.json"

# 5. Cleanup
rm -rf "$TEMP_DATADIR"

echo "Success! rollup.json has been synced."

openssl rand -hex 32 > jwt.txt
echo "Starting L2 node op-geth..."
op-geth \
  --datadir ./l2-data \
  --http \
  --http.port 8545 \
  --http.addr "0.0.0.0" \
  --http.vhosts "*" \
  --http.api "web3,debug,eth,txpool,net,admin,miner,arkiv" \
  --authrpc.addr "localhost" \
  --authrpc.port 8551 \
  --authrpc.vhosts "*" \
  --authrpc.jwtsecret jwt.txt \
  --syncmode=full \
  --gcmode=archive \
  --nodiscover \
  --networkid=42069 \
  --metrics \
  --metrics.addr 0.0.0.0 \
  --metrics.port 6060 \
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

# Wait up to 60 seconds for L2 to produce a block
echo "Waiting for L2 to start producing blocks..."
end=$((SECONDS+60))
NUM_BLOCKS=0

while [ $SECONDS -lt $end ]; do
  # Try to get the block number, suppress error output
  L2_BLOCK=$(cast block-number --rpc-url http://localhost:8545 2>/dev/null || echo "0")

  # Check if block number is a valid integer and greater than 0
  if [[ "$L2_BLOCK" =~ ^[0-9]+$ ]] && [ "$L2_BLOCK" -gt 0 ]; then
    echo "L2 is live! Current block: $L2_BLOCK"

    # Print L1 status as well for confirmation
    L1_BLOCK=$(cast block-number --rpc-url http://localhost:15900)
    echo "L1 Current block: $L1_BLOCK"

    NUM_BLOCKS=$((NUM_BLOCKS+1))
    sleep 1
    continue
  fi

  echo "Waiting for L2... (Current block: $L2_BLOCK)"
  sleep 1
done

tail -f /dev/null
