set -x

anvil -p 25555 &

op-geth --datadir ./l2-data init genesis.json

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

sleep 2

# In a new terminal, while anvil is running
cast block 0 --rpc-url http://localhost:25555 | grep hash | tee hash.txt

op-geth --datadir ./l2-data console --exec "eth.getBlock(0).hash" | tee hash2.txt


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