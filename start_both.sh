# 1. Start L1 (Anvil)
# Note: If your rollup.json expects specific L1 contracts, Anvil must have
# the state from when those configs were generated.
# If this is a fresh run, you might need to redeploy L1 contracts or load a state dump.
anvil -p 25555 &
# 2. Initialize op-geth Database (CRITICAL MISSING STEP)
# You must write the genesis block to the data directory first.
./op-geth --datadir ./l2-data init genesis.json

# 3. Start op-geth
./op-geth \
  --datadir ./l2-data \
  --http \
  --http.port 8545 \
  --http.api "eth,net,engine,web3,debug" \
  --authrpc.addr "localhost" \
  --authrpc.port 8551 \
  --authrpc.vhosts "*" \
  --authrpc.jwtsecret ./jwt.txt \
  --syncmode=full \
  --gcmode=archive \
  --nodiscover \
  --networkid=42069 & # ensure this matches chainId in genesis.json

sleep 2
# 4. Start op-node
# Added: --p2p.sequencer.key (Required to sign blocks)
./op-node \
  --l2=http://localhost:8551 \
  --l2.jwt-secret=./jwt.txt \
  --sequencer.enabled \
  --sequencer.l1-confs=0 \
  --verifier.l1-confs=0 \
  --rollup.config=./rollup.json \
  --rpc.addr=0.0.0.0 \
  --rpc.port=8547 \
  --p2p.disable \
  --l1=http://localhost:25555 \
  --l1.rpckind=basic \
  --p2p.sequencer.key=ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80