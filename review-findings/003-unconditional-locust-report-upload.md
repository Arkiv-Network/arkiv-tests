# Report upload assumes Locust artifacts always exist

**Severity:** Medium

## Affected files

- `.github/workflows/arkiv-system-test.yml:839`
- `.github/workflows/arkiv-system-reth-test.yml:918`
- `.github/workflows/arkiv-system-reth-test.yml:981`

## Problem

Both workflows upload `locust.html` and `locust.log` in an `if: always()` step without checking whether the Locust step actually ran or produced those files.

The op-reth workflow makes this especially likely because `run-locust` defaults to `false` and the workflow has a `Wait indefinitely` step for that mode. Other scenarios, early failures, or skipped Locust runs can also leave the files absent.

## Impact

Cleanup/reporting can fail with a missing local file error and obscure the original workflow result. It also makes non-Locust scenarios look like upload failures rather than cleanly reporting that no Locust report was generated.

## Evidence

The op-geth workflow uploads fixed file paths at `.github/workflows/arkiv-system-test.yml:839-844`:

```bash
curl -sS -X POST -F "file=@locust.html" ...
curl -sS -X POST -F "file=@locust.log" ...
```

The op-reth workflow has `run-locust` gating at `.github/workflows/arkiv-system-reth-test.yml:918-924`, but the upload step at `.github/workflows/arkiv-system-reth-test.yml:981-986` still posts both files unconditionally.

## Suggested fix

Guard each upload with `[ -f locust.html ]` and `[ -f locust.log ]`, or give the Locust step an `id` and condition the upload on the step having run. Keep the upload step `always()` if artifacts should still be preserved after failures.
