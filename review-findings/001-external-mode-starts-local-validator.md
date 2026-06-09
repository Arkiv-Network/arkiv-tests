# External mode still starts local validator services

**Severity:** High

## Affected files

- `.github/workflows/arkiv-system-test.yml:86`
- `.github/workflows/arkiv-system-test.yml:617`
- `.github/workflows/arkiv-system-reth-test.yml:78`
- `.github/workflows/arkiv-system-reth-test.yml:663`

## Problem

Both system-test workflows expose an `is-external` input and an `external-rpc-url`, so callers can run tests against an already deployed network. Most local deployment steps are correctly guarded with `if: ${{ inputs.is-external == 'false' }}`, but the `Start validator node` step is unguarded in both workflows.

When `is-external` is `true`, the workflows skip the binary download, Anvil startup, genesis generation, JWT generation, sequencer startup, and local DA-server startup. They then still run `Start validator node`, which expects local binaries, `validator-data`, `jwt-validator.txt`, `rollup.json`, `anvil-chain.json`, and local sequencer RPCs to exist.

## Impact

External-network runs fail before reaching the steps that actually use `external-rpc-url` for balance snapshots and Locust traffic. This makes the external mode advertised by the workflow inputs unusable.

## Evidence

The op-geth workflow defines external mode at `.github/workflows/arkiv-system-test.yml:86-97`, but `Start validator node` at `.github/workflows/arkiv-system-test.yml:617` has no `if:` guard and immediately starts `op-geth-val` from local data.

The op-reth workflow has the same pattern: external mode is defined at `.github/workflows/arkiv-system-reth-test.yml:78-89`, but `Start validator node` at `.github/workflows/arkiv-system-reth-test.yml:663` has no `if:` guard and first tries to call the local sequencer RPC at `http://localhost:18645`.

## Suggested fix

Add `if: ${{ inputs.is-external == 'false' }}` to both validator startup steps, or split validator startup into a local-only path and an external path that uses the external RPC directly. Also review later cleanup steps so they only kill PID files created by the selected mode.
