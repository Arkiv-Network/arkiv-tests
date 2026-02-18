import asyncio
import os
import socket
import requests
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway, Histogram, Summary
from prometheus_client.parser import text_string_to_metric_families

# --- Configuration ---
JOB_NAME = os.getenv('PROMETHEUS_JOB_NAME', 'geth-metrics-job')
INSTANCE_NAME = os.getenv('PROMETHEUS_INSTANCE_NAME', socket.gethostname())
GETH_SEQ_METRICS_URL = "http://127.0.0.1:6160/debug/metrics/prometheus"
GETH_VAL_METRICS_URL = "http://127.0.0.1:6060/debug/metrics/prometheus"

GATEWAY_URL = os.getenv("PUSH_GATEWAY_URL", "")

# --- 1. Define Registries ---
# This registry is specifically for metrics we want to PUSH to the remote gateway
push_registry = CollectorRegistry()

# Optional: If you had a local web server, you might have a 'local_registry'
# containing ALL metrics. For this script, we just focus on the push one.


def create_no_label_gauge(name, desc):
    return Gauge(name, desc, [], registry=push_registry)

def create_gauge(name, desc):
    return Gauge(name, desc, ["node_type"], registry=push_registry)

def create_summary(name, desc):
    return Summary(name, desc, ["quantile", "node_type"], registry=push_registry)

iteration_gauge = create_no_label_gauge('batch_job_iteration_number', 'The current loop index of the script')
arkiv_free_space = create_no_label_gauge('arkiv_free_space', 'Free space on machine')
arkiv_used_space = create_no_label_gauge('arkiv_used_space', 'Used space on machine')

arkiv_geth_db_size = create_gauge('arkiv_geth_db_size', 'geth database size')
arkiv_da_data_size = create_no_label_gauge('arkiv_da_data_size', 'da data size')

sqlite_db_size = create_gauge('arkiv_sqlite_db_size_bytes', 'The size of the SQLite DB file in bytes')
sqlite_wal_size = create_gauge('arkiv_sqlite_wal_size_bytes', 'The size of the SQLite WAL file in bytes')

def get_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

async def get_path_size_async(path):
    if not os.path.isdir(path): return 0
    process = await asyncio.create_subprocess_exec(
        'du', '-sb', path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await process.communicate()
    return int(stdout.split()[0]) if process.returncode == 0 else 0

async def get_path_size_async_loop(path, metric):
    while True:
        size = await get_path_size_async(path)
        metric.set(size)
        if size < 100000000:
            await asyncio.sleep(1)
        else:
            await asyncio.sleep(10)

async def get_free_disk_space():
    # Execute 'df' for the root directory specifically
    # Using the '/' argument ensures we don't parse unnecessary rows
    proc = await asyncio.create_subprocess_exec(
        'df', '/',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Wait for the command to finish without blocking the event loop
    stdout, stderr = await proc.communicate()

    if proc.returncode == 0:
        lines = stdout.decode().strip().split('\n')
        # Skip header, grab the data line
        data_line = lines[1].split()

        # In 'df' output: index 2 is 'Used' and index 3 is 'Available' blocks (1K each)
        used_kb = int(data_line[2])
        available_kb = int(data_line[3])
        return available_kb * 1024, used_kb * 1024
    else:
        raise RuntimeError(f"df command failed: {stderr.decode()}")


async def get_free_space_async_loop(metric_free, metric_used):
    while True:
        free, taken = await get_free_disk_space()
        if free < 1000000000:
            # @todo implement panic stop whole test to prevent machine
            pass

        metric_free.set(free)
        metric_used.set(taken)
        await asyncio.sleep(1)

async def run_infinite_loop():
    loop_count = 0
    print(f"Starting loop. Pushing selected metrics to {GATEWAY_URL}...")

    # Background task for folder size
    asyncio.create_task(get_path_size_async_loop("sequencer-data/geth", arkiv_geth_db_size.labels(**{'node_type': "sequencer"})))
    asyncio.create_task(get_path_size_async_loop("validator-data/geth", arkiv_geth_db_size.labels(**{'node_type': "validator"})))
    asyncio.create_task(get_path_size_async_loop("da-data", arkiv_da_data_size))

    asyncio.create_task(get_free_space_async_loop(arkiv_free_space, arkiv_used_space))

    while True:
        try:
            loop_count += 1

            # This metric is updated, but NOT pushed (because it's not in push_registry)
            iteration_gauge.set(loop_count)

            # --- 4. Push ONLY the specific registry ---
            push_to_gateway(
                GATEWAY_URL,
                job=JOB_NAME,
                registry=push_registry,  # <--- ONLY metrics in this registry get sent
                grouping_key={'instance': INSTANCE_NAME}
            )

            print(f"Pushed iteration: {loop_count}")
            await asyncio.sleep(1)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(run_infinite_loop())