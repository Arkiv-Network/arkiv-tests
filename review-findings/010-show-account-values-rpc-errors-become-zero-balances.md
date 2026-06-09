# Account metric snapshots treat RPC errors as zero balances

**Severity:** Medium

## Affected files

- `show-account-values.py:15`
- `.github/workflows/arkiv-system-test.yml:745`
- `.github/workflows/arkiv-system-reth-test.yml:874`

## Problem

`show-account-values.py` silently returns `None` for per-account RPC request failures. `fetch_account_values()` then leaves balance and nonce at zero for that account and continues. During comparison mode, those zeros are treated as real account values.

The workflows call this script in the snapshot loop and merge its output into tracker results. A transient RPC error for one address can therefore look like the account spent its full previous balance and sent no transactions.

## Impact

Tracker metrics such as `gasSpentL2`, `totalTransactionsL2`, and `accountsWithTx` can be badly corrupted by partial RPC failures. Because errors are swallowed per account, the workflow may still upload plausible-looking JSON.

## Evidence

`show-account-values.py:15-31` returns `None` on request exceptions. `show-account-values.py:34-58` initializes `balance = 0` and `nonce = 0`, and only changes them when the RPC response contains a result.

In comparison mode, `show-account-values.py:157-169` calculates:

```python
net_balance_decrease += (balance_before - balance_after)
total_transactions += (nonce_after - nonce_before)
```

The snapshot loops invoke the script repeatedly in `.github/workflows/arkiv-system-test.yml:745-778` and `.github/workflows/arkiv-system-reth-test.yml:874-907`.

## Suggested fix

Represent per-account fetch failures explicitly and fail the snapshot, retry, or omit failed accounts from aggregate deltas. Do not convert missing balance or nonce data to zero unless the RPC returned a valid zero result.
