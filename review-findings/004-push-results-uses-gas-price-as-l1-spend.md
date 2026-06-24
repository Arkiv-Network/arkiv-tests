# L1 spend reporting uses gas price instead of spend

**Severity:** High

## Affected files

- `push-results.py:91`
- `gather-metrics.py:467`

## Problem

`push-results.py` reports tracker field `gasSpentL1`, but it reads the latest `arkiv_mainnet_gas_price` measurement from InfluxDB. That measurement is a gas price sample, not cumulative spend.

The collector separately emits cumulative spend metrics:

- `arkiv_simulated_mainnet_spending` per component, in Wei
- `arkiv_simulated_eth_spend` total, in ETH

`push-results.py` ignores those spend metrics and formats the gas price as if it were Wei spent.

## Impact

Tracker results can show a non-zero `gasSpentL1` even when no L1 transactions were observed, or show a value that changes with current gas price rather than actual L1 gas usage. This makes L1 cost summaries misleading.

## Evidence

`push-results.py:91-109` assigns:

```python
simulated_spend_wei = query_last_metric_total(test_name, "arkiv_mainnet_gas_price")
...
result_metrics["gasSpentL1"] = {
    "value": estimated_spend_wei,
    "display": wei_to_eth_str(estimated_spend_wei),
}
```

`gather-metrics.py:467-486` shows that spend is emitted under `arkiv_simulated_mainnet_spending` and `arkiv_simulated_eth_spend`, while `arkiv_mainnet_gas_price` is only the current gas price.

## Suggested fix

Query a spend metric for `gasSpentL1`. Prefer a single total measurement with unambiguous units, for example `arkiv_simulated_eth_spend` converted back to Wei or a new `arkiv_simulated_mainnet_spending_total_wei`. Keep `arkiv_mainnet_gas_price` as a separate display metric if it is useful.
