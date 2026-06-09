# Locust failures are ignored by the workflows

**Severity:** High

## Affected files

- `.github/workflows/arkiv-system-test.yml:789`
- `.github/workflows/arkiv-system-test.yml:807`
- `.github/workflows/arkiv-system-reth-test.yml:923`
- `.github/workflows/arkiv-system-reth-test.yml:941`

## Problem

Both workflows run the write-only Locust stress test with `|| true` appended to the command. That forces the step to succeed even when Locust exits non-zero due to crashes, import errors, RPC failures, assertion failures, or failed test setup.

## Impact

A broken stress test can still produce a green workflow result. Because these workflows are the primary system-test automation, masking the Locust exit status can allow failed load tests to be recorded as successful runs and can make regressions harder to detect.

## Evidence

The op-geth workflow starts Locust at `.github/workflows/arkiv-system-test.yml:789-807` and ends the command with:

```bash
--html "locust.html" > locust.log 2>&1 || true
```

The op-reth workflow repeats the same pattern at `.github/workflows/arkiv-system-reth-test.yml:923-941`.

## Suggested fix

Remove `|| true` from the Locust command. If there are known non-critical Locust exit codes, handle those explicitly after preserving the real status in a variable, upload the report in an `always()` step, and then exit with the original failure status.
