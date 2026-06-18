# Arkiv prod chain — single-validator PoS (reth + Lighthouse)

The prod chain runs **without `--dev`**: execution (arkiv reth) is driven over
the Engine API by a real consensus layer — a single-validator **Lighthouse**
beacon node + validator client.

Forks are active through **Electra / Prague** at genesis. Fulu/Osaka are
intentionally disabled (set to a far-future epoch); Lighthouse's Fulu-at-genesis
support was the one risky piece we chose to skip.

```
arkiv reth (EL) ──Engine API :8551 + JWT── lighthouse beacon (CL) ── lighthouse validator (1 key)
```

## Layout

| Path | Purpose | Committed? |
|---|---|---|
| `config/values.env` | genesis-generator input (chain id, forks, 1 validator, mnemonic) | yes |
| `generate.sh` | produces genesis + keys (run before first start / for a fresh chain) | yes |
| `run-el.sh` | reth entrypoint (init + node, no `--dev`) | yes |
| `docker-compose.yml` | reth + beacon + validator services | yes |
| `.env` | host ports / fee recipient / EL knobs (copy from `.env.example`) | no (gitignored) |
| `output/` | generated EL+CL genesis, JWT (regenerated each `generate.sh`) | no |
| `testnet/` | Lighthouse testnet-dir (config.yaml, genesis.ssz, ...) | no |
| `validators/` | the single validator keystore + secret | no |

## Start a fresh chain

```bash
cd prod
cp .env.example .env            # first time only
./generate.sh                   # stamps genesis at "now", makes keys
docker compose up -d            # start promptly after generate.sh
```

`generate.sh` writes a fresh genesis timestamp (`GENESIS_TIMESTAMP=now`,
`genesis_time = now + GENESIS_DELAY`), so start the stack soon after running it.

Endpoints (default ports):
- EL RPC:     http://127.0.0.1:8545
- EL WS:      ws://127.0.0.1:8546
- EL metrics: http://127.0.0.1:6160
- Beacon API: http://127.0.0.1:5052

## Verify it's working

```bash
# EL blocks advancing (~1 per slot = SECONDS_PER_SLOT, default 6s):
curl -s -X POST http://127.0.0.1:8545 -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Beacon healthy + finalizing (finality appears after ~2 epochs):
curl -s http://127.0.0.1:5052/eth/v1/node/syncing
curl -s http://127.0.0.1:5052/eth/v1/beacon/states/head/finality_checkpoints
```

reth logs show `Received new payload from consensus engine` — that payload now
comes from Lighthouse, not the built-in `--dev` miner.

## Tuning

| Setting | Where | Apply with |
|---|---|---|
| Slot time (block interval) | `SLOT_DURATION_IN_SECONDS` in `config/values.env` | `./generate.sh` + fresh chain |
| Fork schedule / chain id | `config/values.env` | `./generate.sh` + fresh chain |
| Block size (`--builder.gaslimit`) | `BLOCK_GAS_LIMIT` in `.env` | `docker compose up -d reth` (chain preserved) |
| Min fees | `TXPOOL_MIN_PRIORITY_FEE` / `TXPOOL_MIN_PROTOCOL_FEE` in `.env` | `docker compose up -d reth` (chain preserved) |

Note: like the `--dev` setup, block size and fees are reth **startup flags** —
changing them recreates the reth container (a few seconds; the chain/datadir is
preserved). Anything baked into genesis (slot time, forks, chain id) requires a
full regenerate, which is a **new chain**:

```bash
docker compose down -v          # wipe EL + CL volumes
./generate.sh
docker compose up -d
```

## Stop

```bash
docker compose down             # keep chain
docker compose down -v          # also wipe the chain
```

## Notes / limitations

- **Single validator = single point of failure.** Fine for a devnet; it holds
  100% of stake so it finalizes every epoch on its own.
- The validator keystore + mnemonic here are **insecure dev keys** (generated
  with `eth2-val-tools --insecure`). Never reuse them anywhere real.
- Prefunded accounts come from the genesis-generator mnemonic
  (`EL_AND_CL_MNEMONIC` in `config/values.env`). If you need specific accounts
  funded, add them to the generator config and regenerate.
- Versions pinned: genesis generator `6.1.0`, Lighthouse `v8.0.0`,
  reth tag `ARKIV_RETH_TAG` (default `v0.1.0-pure-0`).
