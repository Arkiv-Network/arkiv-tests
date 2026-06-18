# Arkiv pure-reth sequencer — operating notes

A single-node Arkiv reth chain. It runs **execution-only** in reth `--dev` mode:
there is **no separate consensus client**. `--dev` is reth's built-in single
sealer — it drives the Engine API itself and mines a block every
`BLOCK_TIME_SECONDS`. This is the intended "one validator / don't care about
consensus" setup.

## Why no consensus client

The chain is post-merge (Shanghai/Cancun/Prague/Osaka forks are active). On a
post-merge chain the execution client never mines on its own — block production
must be driven over the Engine API. `--dev` is that driver, built in. Running
*without* `--dev` would require an external consensus client (e.g. Lighthouse
with a single validator); we deliberately don't, because `--dev` already gives a
real mempool and a real EIP-1559 fee market.

## Forks

All forks are active from genesis, through **Osaka** (the latest in the reth
2.3.0 binary). This is set in [generate-pure-reth-genesis.py](generate-pure-reth-genesis.py)
via the `*Time: 0` fields (`shanghaiTime`, `cancunTime`, `pragueTime`,
`osakaTime`).

## First start / fresh chain

```bash
./generate_genesis.sh    # writes genesis/genesis.json (all forks)
./start.sh               # init datadir + start the --dev sequencer
```

Endpoints:
- RPC:     http://127.0.0.1:8545
- WS:      ws://127.0.0.1:8546
- Metrics: http://127.0.0.1:6160

Check liveness:
```bash
curl -s -X POST http://127.0.0.1:8545 -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

## Configuration knobs

Set these in `prod/.env` (see [.env.example](.env.example)). All are read at
startup — there is **no runtime RPC** to change them (`miner_setGasLimit` /
`miner_setGasPrice` exist but are no-ops in reth, returning `false`).

| `.env` variable            | Effect                                              | reth flag                        |
|----------------------------|-----------------------------------------------------|----------------------------------|
| `CHAIN_ID`                 | Chain id                                            | genesis `chainId`                |
| `BLOCK_TIME_SECONDS`       | Seconds between blocks                              | `--dev.block-time`               |
| `BLOCK_GAS_LIMIT`          | **Block size** (target gas limit)                  | `--builder.gaslimit`             |
| `TXPOOL_MIN_PRIORITY_FEE`  | Min priority fee (wei) for pool acceptance; optional| `--txpool.minimum-priority-fee`  |
| `TXPOOL_MIN_PROTOCOL_FEE`  | Min protocol base-fee floor (wei); optional         | `--txpool.minimal-protocol-fee`  |

Notes:
- Pinning `BLOCK_GAS_LIMIT` also stops the dev-mode gas-limit auto-creep. When
  you change it, the actual block gas limit walks toward the new target by
  1/1024 per block (standard EIP-1559-style adjustment), not instantly.
- Leave the `TXPOOL_*` vars unset/empty to use reth defaults.
- Values are in **wei**.

## Changing block size or fees during operation

Edit the value in `.env`, then re-create the sequencer. The chain is
**preserved** (the datadir is not wiped — only a genesis change needs that):

```bash
docker compose --env-file .env up -d --force-recreate sequencer
```

This causes a ~2-second block gap, after which the chain continues from the same
height.

## Changing the genesis (forks, chain id, prefunds)

A genesis change alters the genesis hash, so it starts a **new chain** and the
old datadir must be wiped:

```bash
./stop.sh
rm -rf data/*
./generate_genesis.sh
./start.sh
```

## Stop

```bash
./stop.sh
```
