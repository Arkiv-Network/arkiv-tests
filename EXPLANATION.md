# Repository script explanation

This repository contains a mix of helpers for local network setup, test orchestration, tracker integration, and metrics collection. The notes below focus on the Python scripts that live in the main repository root.

## Configuration and network bootstrap

### `generate-intent.py`
- Generates `deploy-config/intent.toml` and `deploy-config/keys.txt`.
- Uses `cast wallet new --json` to create fresh keypairs for the admin, batcher, proposer, signer, and challenger roles.
- Writes an OP Stack-style intent file for a local deployment (`l1ChainID = 31337`) and stores the generated private keys in a companion text file.
- Sets Jovian `minBaseFee` to `10,000,000` wei (`0.01 Gwei`) and asks op-deployer to generate the L2 genesis with the same `baseFeePerGas`.
- Use this when you want a fresh generic deployment config for local testing.

### `generate-intent-arkiv.py`
- Same general job as `generate-intent.py`, but tailored to the Arkiv-flavored deployment shape.
- Generates admin, batcher, proposer, sequencer, and challenger keys, then writes them into `deploy-config/keys.txt`.
- Builds a custom `deploy-config/intent.toml` with Arkiv-specific chain settings, including AltDA-related fields and configurable `L2_BLOCK_TIME` / `L2_GAS_LIMIT`.
- Sets Jovian `minBaseFee` to `10,000,000` wei (`0.01 Gwei`) and asks op-deployer to generate the L2 genesis with the same `baseFeePerGas`.
- Use this when the deployment should match the Arkiv network layout rather than the more generic local template.

### `scripts/set-genesis-base-fee.sh`
- Patches a generated `genesis.json` so top-level `baseFeePerGas` starts at `0x989680`, matching the configured `minBaseFee`.
- Called by `start.sh` and `init_geth-l2.sh` before the L2 datadir is initialized.

### `patch-genesis.py`
- Updates the `alloc` section of a `genesis.json` file so predefined accounts start with funds.
- Reads addresses from `test-accounts.txt` and writes each one into `genesis.json` with a fixed balance of `1000 ETH` (stored in wei).
- This is a quick local helper for prefunding test accounts before starting a chain.
- Note: the script contains reusable helper functions, but the current entrypoint is intentionally simple and hardcoded to `test-accounts.txt` and `genesis.json`, so it is meant to be run from the repository root unless you edit the script.

## Metrics collection and result extraction

### `gather-metrics.py`
- The main long-running metrics collector in this repository.
- Repeatedly gathers:
  - local filesystem usage for sequencer / validator data directories,
  - free disk space,
  - optional Celestia account balances,
  - optional L1 transaction and gas usage metrics for a tracked sender,
  - current mainnet gas price and simulated ETH spend,
  - Prometheus metrics scraped from configured endpoints such as `op-batcher` and `op-proposer`.
- Converts all of those readings into InfluxDB points and pushes them into the configured bucket on a loop.
- This is the script to run when a test environment should continuously emit operational metrics.

### `query-arkiv.py`
- Reads aggregated values back out of InfluxDB for one named test run.
- Queries measurements such as SQLite size, geth database size, WAL size, DA data size, and gas-used statistics for sequencer / validator nodes.
- Produces a JSON summary and writes it to `results.json` (or another file passed with `--save`), merging with an existing file if present.
- This is mainly a post-processing helper used to turn raw InfluxDB data into test-friendly result artifacts.

### `list-influx-measurements.py`
- Connects to InfluxDB and prints the list of measurement names available in the configured bucket.
- Useful for discovering what metrics are present before writing queries or debugging missing measurements.

## RPC inspection and readiness checks

### `show-account-values.py`
- Connects to an Ethereum-style RPC endpoint and inspects a list of addresses.
- For each account it fetches the current balance and nonce, then prints an aggregate summary.
- It can also:
  - save flat numeric metrics for test reporting,
  - save raw account snapshots for later comparison,
  - compare the current state against a previous snapshot to estimate gas spent and transaction counts.
- This is useful for checking whether a test run changed balances / nonces as expected.

### `show-mempool.py`
- Calls the `txpool_content` JSON-RPC method on a Geth-compatible node.
- Prints a readable snapshot of pending and queued mempool transactions, including hash, sender, receiver, value, gas price, nonce, and truncated calldata.
- Useful for debugging stuck or delayed transactions during local testing.

### `wait-for-blocks.py`
- Polls an L2 RPC endpoint until the chain starts producing blocks.
- Optionally also reads the L1 block height while waiting, so logs show both chain states.
- Exits successfully only after it has observed enough successful checks and enough actual block advancement.
- This is a readiness gate for scripts or workflows that must wait until block production is really live.

## Tracker / result reporting helpers

### `notify-test-start.py`
- Sends a `POST` request to the tracker backend at `/test/new`.
- Accepts `key=value` parameters on the command line, converts simple booleans / integers, and sends them as JSON-encoded test metadata.
- Stores the returned test name in `test-name.txt`.
- Use this at the beginning of a run when the external test tracker should register a new test entry.

### `push-results.py`
- Reads a JSON results file and posts it to the tracker backend at `/test/<name>/results`.
- Wraps the file content inside a payload containing `parameters` and total runtime in `seconds`.
- When InfluxDB data is available for the same test name, it also enriches the payload with L1 transaction count and estimated L1 spend using the metrics emitted by `gather-metrics.py`.
- Use this after a run is complete so the tracker can store the final metrics or assertions.

## Small utility script

### `name-gen.py`
- Generates a random synthetic name from hardcoded prefix / suffix pools plus a random number.
- Prints one generated name immediately when the script runs.
- This is just a lightweight helper for creating memorable identifiers for tests or environments.
