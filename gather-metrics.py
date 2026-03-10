import asyncio
import math
import os
import socket

import requests
from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from prometheus_client.parser import text_string_to_metric_families

# --- Configuration ---
JOB_NAME = os.getenv("JOB_NAME", "geth-metrics-job")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", socket.gethostname())
PUSH_INTERVAL_SECONDS = float(os.getenv("METRICS_PUSH_INTERVAL_SECONDS", "1"))

SCRAPE_TARGETS = {
    "op-batcher": os.getenv(
        "OP_BATCHER_METRICS_URL", "http://127.0.0.1:7365/metrics"
    ),
    "op-proposer": os.getenv(
        "OP_PROPOSER_METRICS_URL", "http://127.0.0.1:7375/metrics"
    ),
}

# InfluxDB v2 specifics
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-auth-token")
INFLUX_ORG = os.getenv("INFLUXDB_ORG", "arkiv-network")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "arkiv-tests")

# --- State Management ---
# Since we don't have Prometheus 'Gauge' objects holding state anymore,
# we'll use a simple dictionary to hold the latest metric values.
metrics_state = {
    "batch_job_iteration_number": 0,
    "arkiv_free_space": 0,
    "arkiv_used_space": 0,
    "arkiv_da_data_size": 0,
    "arkiv_geth_db_size": {"sequencer": 0, "validator": 0},
    "arkiv_sqlite_db_size_bytes": {"sequencer": 0, "validator": 0},
    "arkiv_sqlite_wal_size_bytes": {"sequencer": 0, "validator": 0},
}


def get_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


async def get_path_size_async(path):
    if not os.path.isdir(path):
        return 0

    process = await asyncio.create_subprocess_exec(
        "du",
        "-sb",
        path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    return int(stdout.split()[0]) if process.returncode == 0 else 0


async def get_path_size_async_loop(path, metric_key, node_type=None):
    while True:
        size = await get_path_size_async(path)

        # Update the state dictionary instead of a Prometheus Gauge
        if node_type:
            metrics_state[metric_key][node_type] = size
        else:
            metrics_state[metric_key] = size

        if size < 100000000:
            await asyncio.sleep(1)
        else:
            await asyncio.sleep(10)


async def get_free_disk_space():
    proc = await asyncio.create_subprocess_exec(
        "df",
        "/",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode == 0:
        lines = stdout.decode().strip().split("\n")
        data_line = lines[1].split()

        used_kb = int(data_line[2])
        available_kb = int(data_line[3])
        return available_kb * 1024, used_kb * 1024

    raise RuntimeError(f"df command failed: {stderr.decode()}")


async def get_free_space_async_loop():
    while True:
        free, taken = await get_free_disk_space()
        if free < 1000000000:
            # @todo implement panic stop whole test to prevent machine
            pass

        metrics_state["arkiv_free_space"] = free
        metrics_state["arkiv_used_space"] = taken
        await asyncio.sleep(1)



def create_point(measurement, value, tags=None):
    point = Point(measurement).tag("test", JOB_NAME).tag("instance", INSTANCE_NAME)
    for tag_key, tag_value in (tags or {}).items():
        point = point.tag(tag_key, str(tag_value))

    # Field name "value" is a standard convention for single-value metrics
    return point.field("value", float(value))



def scrape_prometheus_target(target_name, url):
    response = requests.get(url, timeout=5)
    response.raise_for_status()

    points = []
    for family in text_string_to_metric_families(response.text):
        for sample in family.samples:
            value = float(sample.value)
            if not math.isfinite(value):
                continue

            sample_tags = {"component": target_name}
            sample_tags.update(sample.labels)
            points.append(create_point(sample.name, value, sample_tags))

    return points


async def collect_scraped_metrics_points():
    scrape_target_items = [(target_name, url) for target_name, url in SCRAPE_TARGETS.items() if url]
    if not scrape_target_items:
        return []

    results = await asyncio.gather(
        *[
            asyncio.to_thread(scrape_prometheus_target, target_name, url)
            for target_name, url in scrape_target_items
        ],
        return_exceptions=True,
    )

    points = []
    for (target_name, _), result in zip(scrape_target_items, results, strict=False):
        if isinstance(result, Exception):
            print(f"Failed to scrape {target_name} metrics: {result}")
            continue

        points.extend(result)

    return points


async def run_infinite_loop():
    loop_count = 0
    print(f"Starting loop. Pushing selected metrics to InfluxDB at {INFLUXDB_URL}...")

    # Background task for folder size
    asyncio.create_task(
        get_path_size_async_loop("sequencer-data/geth", "arkiv_geth_db_size", "sequencer")
    )
    asyncio.create_task(
        get_path_size_async_loop("validator-data/geth", "arkiv_geth_db_size", "validator")
    )
    asyncio.create_task(get_path_size_async_loop("da-data", "arkiv_da_data_size"))
    asyncio.create_task(get_free_space_async_loop())

    # Initialize the Async InfluxDB Client
    async with InfluxDBClientAsync(
        url=INFLUXDB_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG,
    ) as client:
        write_api = client.write_api()

        while True:
            try:
                loop_count += 1
                metrics_state["batch_job_iteration_number"] = loop_count

                # Update SQLite file sizes directly in the state
                metrics_state["arkiv_sqlite_db_size_bytes"]["sequencer"] = get_file_size(
                    "sequencer-data/golem-base.db"
                )
                metrics_state["arkiv_sqlite_wal_size_bytes"]["sequencer"] = get_file_size(
                    "sequencer-data/golem-base.db-wal"
                )

                metrics_state["arkiv_sqlite_db_size_bytes"]["validator"] = get_file_size(
                    "validator-data/golem-base.db"
                )
                metrics_state["arkiv_sqlite_wal_size_bytes"]["validator"] = get_file_size(
                    "validator-data/golem-base.db-wal"
                )

                # --- Build InfluxDB Points ---
                points = []

                # Translate our state dictionary into InfluxDB Points
                for key, val in metrics_state.items():
                    if isinstance(val, dict):
                        for node_type, size in val.items():
                            points.append(create_point(key, size, {"node": node_type}))
                    else:
                        points.append(create_point(key, val))

                points.extend(await collect_scraped_metrics_points())

                # --- Push to InfluxDB ---
                await write_api.write(bucket=INFLUX_BUCKET, record=points)

                print(f"Pushed iteration: {loop_count}")
                await asyncio.sleep(PUSH_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(run_infinite_loop())
