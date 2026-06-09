# Write-only Locust users generate duplicate entity IDs

**Severity:** High

## Affected files

- `stress/l3/dc_write_only.py:138`
- `stress/tools/dc_data.py:225`
- `stress/l3/dc_read_and_write.py:350`

## Problem

`dc_write_only.py` claims each user maintains unique entity IDs, but it never initializes `self.seed`. The class attribute remains `None`, and every Locust user starts with the same per-user counters. The deterministic ID helpers include the seed, node number, and workload number, so equal seeds and equal counters produce identical node IDs, workload IDs, entity keys, and payloads across users.

The mixed read/write test demonstrates the missing setup: it defines `on_start()` and sets `self.seed = self.id`, then resets the counters.

## Impact

Multi-user write-only tests do not create independent data. Users collide on the same deterministic node/workload IDs and entity keys, which can turn a load test into repeated overwrites, duplicate-key failures, or misleading throughput measurements.

## Evidence

`dc_write_only.py:146-150` defines `seed: int = None`. The task passes that unchanged seed into `create_node()` and `create_workload()` at `dc_write_only.py:240-247` and `dc_write_only.py:277-285`.

`stress/tools/dc_data.py:225-247` uses the seed to derive node IDs, workload IDs, and entity keys. With `seed=None`, user 0 and user 1 both generate the same IDs for their first node and first workloads.

`dc_read_and_write.py:350-363` contains the expected initialization path:

```python
self.seed = self.id
self.node_counter = 0
self.workload_counter = 0
self.current_block = DEFAULT_BLOCK
```

## Suggested fix

Add an `on_start()` method to `DataCenterUser` in `dc_write_only.py` that calls `super().on_start()`, sets `self.seed = self.id`, resets the counters, and applies any intended per-user randomization. Consider adding a unit test that two users with different IDs produce different first entity keys.
