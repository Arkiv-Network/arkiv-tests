set -x


op-geth --datadir ./l2-data init genesis.json

op-geth --datadir ./l2-data console --exec "eth.getBlock(0).hash" | tee l2-hash.txt

echo "L2 Genesis Hash:"
cat l2-hash.txt

anvil -p 25555 &

sleep 2

# In a new terminal, while anvil is running
cast block 0 --rpc-url http://localhost:25555 | grep hash | tee l1-hash.txt

#!/bin/bash

# 1. Define the hashes (Cleaned from your text files)
L1_HASH=$(awk '{print $2}' l1-hash.txt | sed "s/['\"]//g")
L2_HASH=$(awk '{print $1}' l2-hash.txt | sed "s/['\"]//g")

echo "Extracted L1 Genesis Hash: $L1_HASH"
echo "Extracted L2 Genesis Hash: $L2_HASH"

# 2. Use sed to replace the placeholders in place
sed -i "s/REPLACE_WITH_YOUR_ANVIL_GENESIS_HASH/$L1_HASH/g" ./rollup.json
sed -i "s/REPLACE_WITH_YOUR_OP_GETH_GENESIS_HASH/$L2_HASH/g" ./rollup.json

echo "✅ rollup.json updated successfully!"
grep -E "hash" ./rollup.json

# 3. Start op-geth
op-geth \
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


# 4. Start op-node
# Added: --p2p.sequencer.key (Required to sign blocks)
op-node \
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