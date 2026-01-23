set -x
set -e

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
  --networkid=42069 \
  2>&1 | tee "op-geth.log" &

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
  --l1=http://localhost:15900 \
  --l1.rpckind=basic \
  --p2p.sequencer.key=ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  2>&1 | tee "op-node.log" &