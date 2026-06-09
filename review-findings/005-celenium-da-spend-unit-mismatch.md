# Celenium DA spend units are inconsistent and tests fail

**Severity:** High

## Affected files

- `gather-metrics.py:493`
- `gather-metrics.py:570`
- `METRICS.md:60`
- `tests/test_gather_metrics.py:378`

## Problem

The Celenium simulated DA spend code, documentation, and tests disagree about the unit stored in `simulated_da_spending_total`.

The docs and tests treat `arkiv_simulated_da_spending` as uTIA. They calculate the cumulative value as:

```text
(90000 + 8.5 * delta_bytes) * median_gas_price
```

and convert to USD as:

```text
arkiv_simulated_da_spending / 1e6 * tia_price_usd
```

The implementation divides by `1e6` during accumulation, but then multiplies the stored value directly by USD price. That mixes old uTIA state with new TIA increments and makes the USD metric too large when existing state is in uTIA.

## Impact

DA cost metrics are wrong, and the current unit tests fail. This undermines cost dashboards and any tracker summaries that rely on `arkiv_simulated_da_spending` or `arkiv_simulated_da_spending_usd`.

## Evidence

`gather-metrics.py:503-506` divides by `1e6` while updating the total:

```python
estimated_pfb_gas * gas_price / Decimal("1000000")
```

`gather-metrics.py:592-596` later computes USD with:

```python
da_spending_usd = float(simulated_da_spending_total) * tia_price_usd
```

`METRICS.md:62-69` describes the spend metric as the raw simulated spend and says USD should be computed as `arkiv_simulated_da_spending / 1e6 * arkiv_tia_price_usd`.

Running `python3 -m unittest discover -s tests -v` fails four Celenium tests, including `test_collect_celenium_gas_metrics_tracks_da_spending_from_size_diff`, where the test expects `381.9951` but the implementation returns `1.5003804951`.

## Suggested fix

Pick one canonical unit and apply it everywhere. The least disruptive fix is to keep `arkiv_simulated_da_spending` in uTIA as documented and tested, remove the division from accumulation, and divide by `1e6` only when computing USD. Alternatively, rename the metric to make TIA units explicit and update tests/docs/state initialization together.
