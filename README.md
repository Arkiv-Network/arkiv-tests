## Note for external collaborators

this is only part of greater system which is not yet fully public.

Use this only as a reference. 

## Test tracker is the place to go

[Test Tracker - Main page](https://tracker.arkiv-global.net)

## Visual overview of the system

![Overview](Overview.png)

## Documentation

- [Script explanation](EXPLANATION.md)
- [Metrics reference](METRICS.md)

## op-batcher-collector

`Dockerfile.standard` installs `op-batcher-collector` from the
`Arkiv-Network/op-batcher-collector` GitHub releases. The default build version
is `v1.2.0` and can be changed with:

```sh
docker build -f Dockerfile.standard --build-arg OP_BATCHER_COLLECTOR_VERSION=v1.2.0 .
```

`start.sh` starts `op-batcher`, waits for its admin RPC on port `8548`, then
starts `op-batcher-collector`. The collector polls `admin_getThrottleController`
through `BATCHER_RPC_URL` and exposes the API that `arkiv-chain-indexer` should
consume instead of talking to the batcher RPC directly.

Default local endpoints:

| Service | Endpoint |
| --- | --- |
| op-batcher RPC | `http://127.0.0.1:8548` |
| op-batcher-collector API | `http://127.0.0.1:28881` |

Useful collector endpoints are `/health`, `/latest`, and `/history`. Runtime
overrides use the collector's upstream environment variables:
`BATCHER_RPC_URL`, `HISTORY_SIZE`, `COLLECTOR_LISTEN_HOST`, and
`COLLECTOR_LISTEN_PORT`.

## Other stuff

### useful greps for op batcher logs debugging

cat op-batcher.log | grep "Loading range of multiple blocks into state" 

cat op-batcher.log | grep "Added L2 block to local state"
