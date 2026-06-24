# query-arkiv.py interpolates Flux filters without escaping

**Severity:** Medium

## Affected files

- `query-arkiv.py:19`
- `query-arkiv.py:64`
- `push-results.py:41`

## Problem

`query-arkiv.py` builds Flux queries by directly interpolating `test_name`, `measurement`, and `node_type` into string literals. The script accepts `--test_name` from the command line and the workflows pass tracker-generated test names into it.

If any interpolated value contains a quote, backslash, newline, or Flux syntax, the query can fail or match unintended data. This is also inconsistent with `push-results.py`, which already has a helper to escape Flux strings before interpolation.

## Impact

Tracker uploads can lose metrics for tests whose names contain special characters. If a test name is ever influenced by user-controlled input, the unescaped interpolation also risks Flux query injection.

## Evidence

`query-arkiv.py:31-38`, `query-arkiv.py:73-81`, and `query-arkiv.py:111-120` directly interpolate values into Flux:

```python
|> filter(fn: (r) => r["_measurement"] == "{measurement}")
|> filter(fn: (r) => r["test"] == "{test_name}")
```

`push-results.py:41-50` contains `escape_flux_string()`, showing that the repository already recognizes this escaping requirement for Flux queries.

## Suggested fix

Reuse the same Flux escaping helper in `query-arkiv.py` for every string literal, including bucket, measurement, test name, and node type. Add a unit test with a quoted test name similar to `test_query_last_metric_total_escapes_flux_strings` in `tests/test_push_results.py`.
