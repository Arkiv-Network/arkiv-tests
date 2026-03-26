# Metrics gathered by the system

This repository primarily gathers metrics through `gather-metrics.py`, which continuously writes measurements into InfluxDB for one test run.

Every point emitted by the collector includes these base tags:

- `test` - the current test or job name (`JOB_NAME`)
- `instance` - the hostname or configured instance name (`INSTANCE_NAME`)

Some measurements also add extra tags such as `node`, `component`, `sender`, `address`, `denom`, `tx_hash`, `block_number`, `to`, or labels copied from scraped Prometheus endpoints.

For a higher-level description of the scripts involved, see [EXPLANATION.md](EXPLANATION.md).

## Core filesystem and host metrics

| Measurement | Meaning | Typical tags |
| --- | --- | --- |
| `batch_job_iteration_number` | Counter-like loop number for the metrics collector itself. Useful for confirming that the collector is still running. | none beyond base tags |
| `arkiv_free_space` | Free space on `/`, in bytes. | none beyond base tags |
| `arkiv_used_space` | Used space on `/`, in bytes. | none beyond base tags |
| `arkiv_da_data_size` | Total size of the `da-data` directory, in bytes. | none beyond base tags |
| `arkiv_geth_db_size` | Size of the `sequencer-data/geth` or `validator-data/geth` directory, in bytes. | `node=sequencer` or `node=validator` |
| `arkiv_sqlite_db_size_bytes` | Size of the `golem-base.db` database file for each node, in bytes. | `node=sequencer` or `node=validator` |
| `arkiv_sqlite_wal_size_bytes` | Size of the SQLite WAL file (`golem-base.db-wal`) for each node, in bytes. | `node=sequencer` or `node=validator` |
| `arkiv_pebble_db_size` | Size of the path currently tracked for the Pebble database metric, emitted per node. | `node=sequencer` or `node=validator` |

## Optional Celestia metric

This metric is only emitted when both `CELESTIA_ADDRESS` and `CELESTIA_RPC_ADDR` are configured.

| Measurement | Meaning | Typical tags |
| --- | --- | --- |
| `arkiv_celestia_account_balance` | Current Celestia account balance for the configured address, currently recorded for the `utia` denomination. | `address`, `denom=utia` |

## Optional L1 sender tracking metrics

These metrics are emitted when `OP_NODE_L1_RPC_URL` is configured together with at least one tracked sender address such as `OP_NODE_L1_ADDRESS`, `OP_BATCHER_L1_ADDRESS`, or `OP_PROPOSER_L1_ADDRESS`. The collector scans L1 blocks, finds transactions sent by those addresses, and emits both per-transaction and cumulative measurements.

| Measurement | Meaning | Typical tags |
| --- | --- | --- |
| `arkiv_l1_transaction_gas_used` | Gas used by each matching L1 transaction. One point is emitted per transaction. | `component`, `sender`, `tx_hash`, `block_number`, `to` |
| `arkiv_l1_transactions_total` | Running total of matching L1 transactions seen so far. | `component`, `sender` |
| `arkiv_l1_gas_used_total` | Running total of gas used by matching L1 transactions. | `component`, `sender` |
| `arkiv_l1_last_scanned_block` | Highest L1 block number scanned by the collector. | `component`, `sender` |

At the moment the tracked sender map can include `component=op-node`, `component=op-batcher`, and `component=op-proposer`.

## Mainnet gas price and simulated spend metrics

These metrics are emitted when `GAS_BASE_NETWORK` is configured. The collector fetches `eth_gasPrice` from the configured network and combines it with the cumulative L1 gas totals.

| Measurement | Meaning | Typical tags |
| --- | --- | --- |
| `arkiv_mainnet_gas_price` | Current gas price returned by the configured mainnet RPC, in wei. | none beyond base tags |
| `arkiv_simulated_eth_spend` | Estimated ETH spend computed as `arkiv_l1_gas_used_total * arkiv_mainnet_gas_price / 1e18`. | `component` |

## Scraped Prometheus metrics

The collector can also scrape Prometheus endpoints and forward all numeric samples directly into InfluxDB. By default it targets:

- `op-batcher` from `OP_BATCHER_METRICS_URL`
- `op-proposer` from `OP_PROPOSER_METRICS_URL`

These measurements keep the original Prometheus sample name as the InfluxDB measurement name. Each emitted point includes:

- `component=<scrape target name>` such as `op-batcher` or `op-proposer`
- all labels that were present on the Prometheus sample

This means measurements such as Geth or OP Stack metrics can appear in InfluxDB exactly as exposed by the scraped endpoint, for example:

- `geth.chain/head/gas_used_hist.histogram`
- `geth.chain/head/gas_used.gauge`

## Metrics used by result extraction

`query-arkiv.py` reads a subset of the collected measurements back from InfluxDB to build `results.json`. The main summary values currently come from:

- `arkiv_sqlite_db_size_bytes`
- `arkiv_geth_db_size`
- `arkiv_sqlite_wal_size_bytes`
- `arkiv_da_data_size`
- `geth.chain/head/gas_used_hist.histogram`
- `geth.chain/head/gas_used.gauge`

Those queries are used to produce compact per-test result artifacts after a run completes.
