# Dockerfile.standard omits files and tools required by start.sh

**Severity:** High

## Affected files

- `Dockerfile.standard:1`
- `start.sh:1`
- `patch-genesis.py:76`

## Problem

`Dockerfile.standard` builds an image whose entrypoint is `start.sh`, but it does not include all files and tools that `start.sh` requires.

The image only copies:

- `start.sh`
- `generate-intent.py`
- `anvil-chain.json`

The entrypoint also requires:

- `jq`, used before any Python scripts run
- `patch-genesis.py`, invoked by `start.sh`
- `test-accounts.txt`, read by `patch-genesis.py`

## Impact

The standard Docker image cannot complete startup. It will fail at the first missing dependency (`jq` if not installed in the base image, then `patch-genesis.py` or `test-accounts.txt`), so the advertised containerized standard environment is not reproducible from this Dockerfile.

## Evidence

`Dockerfile.standard:9-14` copies only three repo files into `/app` and starts `/bin/bash start.sh`.

`start.sh:3-4` calls `jq`, and `start.sh:16-17` invokes `python patch-genesis.py`.

`patch-genesis.py:76-81` reads `test-accounts.txt` and patches `genesis.json`.

## Suggested fix

Install `jq` in `Dockerfile.standard`, copy `patch-genesis.py` and `test-accounts.txt`, and consider copying all runtime scripts as an explicit group. Add a smoke test such as `docker build -f Dockerfile.standard .` plus a short entrypoint dry-run or dependency check.
