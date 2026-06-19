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
| `config/values.env` | genesis-generator input (chain id, forks, prefunded-account mnemonic) | yes |
| `generate-env.sh` | writes `.env` with separate operator EVM key and validator BLS key | yes |
| `install-sdk-js.sh` | builds `arkiv-sdk-js` from `ARKIV_SDK_JS_REF` and installs the tarball | yes |
| `generate.sh` | produces genesis + validator keystore from explicit keys | yes |
| `run-el.sh` | reth entrypoint (init + node, no `--dev`) | yes |
| `docker-compose.yml` | reth + beacon + validator services | yes |
| `.env` | host ports / test account words / operator key / validator key / EL knobs | no (gitignored) |
| `output/` | generated EL+CL genesis, JWT (regenerated each `generate.sh`) | no |
| `testnet/` | Lighthouse testnet-dir (config.yaml, genesis.ssz, ...) | no |
| `validators/` | the single validator keystore + secret | no |

## Start a fresh chain

```bash
cd prod
./generate-env.sh               # first time only, or provide your own .env
./install-sdk-js.sh             # builds the requested Arkiv JS SDK branch/ref
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
| Arkiv JS SDK branch/ref | `ARKIV_SDK_JS_REF` in `.env` | `./install-sdk-js.sh` |
| Prefunded test accounts | `TEST_ACCOUNTS_MNEMONIC` in `.env` | `./generate.sh` + fresh chain |
| Operator / fee recipient | `OPERATOR_PRIVATE_KEY` + `OPERATOR_ADDRESS` in `.env` | `docker compose up -d beacon validator` |
| Validator key | `VALIDATOR_PRIVATE_KEY` + `VALIDATOR_ADDRESS` in `.env` | `./generate.sh` + fresh chain |
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

## Surviving a machine reboot

The stack is designed to come back automatically after the host reboots:

- All three services use `restart: unless-stopped`, so Docker restarts them on
  boot (and on crash), unless you explicitly `docker compose stop`/`down` them.
- Chain state persists across reboots: the EL/CL databases live in the named
  volumes `reth-data` / `beacon-data`, and genesis + validator keys + slashing
  protection are the `output/`, `testnet/`, `validators/` bind mounts. On
  restart the chain **resumes** — `run-el.sh` skips re-init when the datadir is
  non-empty, so there is no new genesis.

Two host-level requirements (not expressible in compose):

1. **The Docker daemon must start on boot.** This is the usual reason a stack
   doesn't come back. On Linux: `sudo systemctl enable --now docker`. (On
   Windows/Docker Desktop the daemon only runs after a user logs in unless you
   configure it otherwise — prefer a Linux host for an always-on node.)
2. **Bring the stack up once** with `docker compose up -d`; thereafter reboots
   are handled by the restart policy.

Note: `depends_on` only orders startup for `docker compose up`, not for the
daemon's reboot auto-restart — on reboot the three containers may start in any
order. That is fine here: the beacon retries its connection to reth's Engine
API and the validator retries its connection to the beacon, so the stack
converges on its own.

## Notes / limitations

- **Single validator = single point of failure.** Fine for a devnet; it holds
  100% of stake so it finalizes every epoch on its own.
- `generate-env.sh` creates fresh private keys for convenience. For production,
  you can provide your own `.env` instead. `OPERATOR_ADDRESS` must match
  `OPERATOR_PRIVATE_KEY`; `VALIDATOR_ADDRESS` is the BLS public key derived
  from `VALIDATOR_PRIVATE_KEY`.
- Prefunded execution-layer accounts come from `TEST_ACCOUNTS_MNEMONIC` in
  `.env`, which overrides the generator's `EL_AND_CL_MNEMONIC` at generation
  time.
- The operator is the block proposer fee recipient (`OPERATOR_ADDRESS` in
  `.env`). The validator is injected into genesis via
  `config/additional-validators.txt`, generated from `VALIDATOR_ADDRESS`.
  Neither is derived from the prefunded account mnemonic. If you need specific
  accounts funded, add them to the generator config and regenerate.
- Versions pinned: genesis generator `6.1.0`, Lighthouse `v8.0.0`,
  reth tag `ARKIV_RETH_TAG` (default `v0.1.0-pure-0`).
