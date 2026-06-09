# start.sh exits after the wait loop instead of keeping the chain alive

**Severity:** High

## Affected files

- `Dockerfile.standard:14`
- `start.sh:58`

## Problem

`start.sh` starts Anvil, op-geth, and op-node in the background, waits up to 60 seconds, and then reaches end-of-file. Because `Dockerfile.standard` uses this script as the container entrypoint, PID 1 exits after the wait loop. The container then stops, taking the background chain processes with it.

The wait loop also does not fail if L2 never becomes live. If no blocks are produced, the loop ends after 60 seconds and the script exits with status 0 because there is no final validation.

## Impact

The standard container does not keep the local chain running. It can also report a successful startup even when L2 never produced a block, which makes automation think the service is healthy when it is not.

## Evidence

`Dockerfile.standard:14` sets:

```dockerfile
ENTRYPOINT ["/bin/bash", "start.sh"]
```

`start.sh:58-82` loops until `SECONDS` reaches the deadline. On successful block production it prints status and `continue`s; on timeout it simply falls out of the loop. There is no `exit 1` on failure and no `wait` or foreground process after the loop.

## Suggested fix

Track whether the required number of L2 blocks was observed. Exit non-zero if startup fails. If startup succeeds, keep the container alive by waiting on the child processes or running the main node in the foreground.
