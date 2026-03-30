# Experiment Results

## Experiment Overview

Two experiments were conducted to evaluate Arkiv network performance under different DA (Data Availability) size configurations. Both experiments processed **111,500 blocks** with a block interval of **2 seconds**, resulting in a total experiment duration of approximately **61.9 hours (~2.6 days)** per run.

| Parameter | Value |
| --- | --- |
| Total blocks | 111,500 |
| Block interval | 2 seconds |
| Total duration | 223,000 seconds ≈ 61.9 hours ≈ 2.6 days |

## Results Summary

### Storage & Throughput

| Metric | Experiment 1 (100K DA) | Experiment 2 (200K DA) |
| --- | --- | --- |
| Max DA size | 100,000 | 200,000 |
| Create operations | 500,000 | 1,248,000 |
| Created data | 1.41 GB | 3.49 GB |
| Geth DB (Sequencer) | 5.58 GB | 12.2 GB |
| Geth DB (Validator) | 1.81 GB | 3.92 GB |
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

## Key Observations

- **Doubling the DA size** (100K → 200K) resulted in roughly **2.5× more create operations** (500K → 1.25M) and **2.5× more created data** (1.41 GB → 3.49 GB).
- **DA throughput doubled** from 6,500 to 13,000 bytes/sec, scaling linearly with the DA size limit.
- **Commitment counts remained stable** (~18,500–18,630) across both configurations, with nearly identical gas costs per commitment (~21,400 gas).
- **ETH spending was virtually identical** between both experiments (~0.041 ETH / ~$95 USD), indicating that L1 commitment costs are independent of DA volume.
- **TIA spending scales with data volume** — roughly doubling from 55.8 TIA ($16.80) to 108 TIA ($32.50) as the DA size doubled.
- **TIA cost per MB decreased** from $0.042/MB to $0.037/MB with higher throughput, showing favorable economies of scale on the DA layer.
