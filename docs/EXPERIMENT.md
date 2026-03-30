# Experiment Results

## Experiment Overview

Two experiments were conducted during weekend 27.03.26-30.03.26 to evaluate Arkiv network performance under different DA (Data Availability) size configurations. Both experiments processed **111,500 blocks** with a block interval of **2 seconds**, resulting in a total experiment duration of approximately **61.9 hours (~2.6 days)** per run.

| Parameter | Value |
| --- | --- |
| Total blocks | 111,500 |
| Block interval | 2 seconds |
| Total duration | 223,000 seconds ≈ 61.9 hours ≈ 2.6 days |

## Results Summary

### Storage & Throughput

| Metric | Experiment 1 (100K DA) | Experiment 2 (200K DA) |
| --- | --- | --- |
| Max DA size (parameter given) | 100,000 | 200,000 |
| Create operations | 500,000 | 1,248,000 |
| Created data | 1.41 GB | 3.49 GB |
| Geth DB (Sequencer - archive node) | 5.58 GB | 12.2 GB |
| Geth DB (Validator - full node) | 1.81 GB | 3.92 GB |
| DA data | 1.33 GB | 2.94 GB |
| Gas per block | 700,000 | 1,900,000 |
| DA throughput | 6,500 bytes/sec | 13,000 bytes/sec |

### Commitments

| Metric | Experiment 1 (100K DA) | Experiment 2 (200K DA) |
| --- | --- | --- |
| Total commitments | 18,630 | 18,500 |
| Total commitments gas | 398,000,000 | 396,000,000 |
| Gas per commitment | ~21,363 | ~21,406 |

### Cost Analysis

| Metric | Experiment 1 (100K DA) | Experiment 2 (200K DA) |
| --- | --- | --- |
| ETH spending | 0.0410 ETH | 0.0409 ETH |
| ETH spending (USD) | $95.10 | $94.70 |
| TIA spending | 55.8 TIA | 108 TIA |
| TIA spending (USD) | $16.80 | $32.50 |
| TIA price per MB | $0.042/MB | $0.037/MB |

## Results Normalized per Day

All values below are the totals divided by the experiment duration of ~2.58 days (223,000 seconds).

### Daily Storage Growth

| Metric | Experiment 1 (100K DA) | Experiment 2 (200K DA) |
| --- | --- | --- |
| Blocks per day | 43,200 | 43,200 |
| Create operations per day | ~193,700 | ~483,500 |
| Created data per day | 0.55 GB | 1.35 GB |
| Geth DB growth per day (Sequencer) | 2.16 GB | 4.73 GB |
| Geth DB growth per day (Validator) | 0.70 GB | 1.52 GB |
| DA data per day | 0.52 GB | 1.14 GB |

### Daily Commitments

| Metric | Experiment 1 (100K DA) | Experiment 2 (200K DA) |
| --- | --- | --- |
| Commitments per day | ~7,220 | ~7,170 |
| Commitments gas per day | ~154,200,000 | ~153,400,000 |

### Daily Cost

| Metric | Experiment 1 (100K DA) | Experiment 2 (200K DA) |
| --- | --- | --- |
| ETH spending per day | 0.0159 ETH | 0.0159 ETH |
| ETH spending per day (USD) | $36.84 | $36.69 |
| TIA spending per day | 21.6 TIA | 41.8 TIA |
| TIA spending per day (USD) | $6.51 | $12.59 |

## Important

Don't use geth db sizes or creates at given, they are depending on what data is how well it compresses, how much empty blocks are and many more. 
The values shown can be used to build an intuition about the orders of magnitude we are talking about.

So the full data throuput may be exactly da bytes or greater depending on compression

## Note

The gas prices during the weekend were really low. More important is that we are using like 150m gas per day. Given gas prices charts we can easily compute

| Gas Price (Gwei) | Gas Limit | Transaction Fee (ETH) | Transaction Fee (USD) |
| :--- | :--- | :--- | :--- |
| **0.1** | 155,000,000 | 0.0155 ETH | $31.00 |
| **1.0** | 155,000,000 | 0.1550 ETH | $310.00 |
| **10.0** | 155,000,000 | 1.5500 ETH | $3,100.00 |

The same principle is with TIA, right now gas prices are quite cheap but may raise in future (but they should be much less volatile than ETH prices)

