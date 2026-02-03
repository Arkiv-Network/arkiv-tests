import asyncio
import os
import socket
import time
import requests
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from prometheus_client.parser import text_string_to_metric_families

# --- Configuration ---
JOB_NAME = os.getenv('PROMETHEUS_JOB_NAME', 'geth-metrics-job')
INSTANCE_NAME = os.getenv('PROMETHEUS_INSTANCE_NAME', socket.gethostname())
GETH_METRICS_URL = "http://127.0.0.1:6060/debug/metrics/prometheus"
GATEWAY_URL = 'https://l2.arkiv-global.net/eKUSzE1KvC'

# --- 1. Define Registries ---
# This registry is specifically for metrics we want to PUSH to the remote gateway
push_registry = CollectorRegistry()

# Optional: If you had a local web server, you might have a 'local_registry'
# containing ALL metrics. For this script, we just focus on the push one.

# --- 2. Define Gauges (Detached) ---
# We use registry=None so we can manually decide which registry they belong to later.
def create_gauge(name, desc):
    return Gauge(name, desc, [], registry=push_registry)

# -- Metrics we WANT to push --
current_head_gauge = create_gauge('chain_head_block_number', 'The current chain head block number from Geth')
arkiv_geth_db_size = create_gauge('arkiv_geth_db_size', 'Number of arkiv database size')
sqlite_wal_size = create_gauge('sqlite_wal_file_size_bytes', 'The size of the SQLite WAL file in bytes')

# -- Metrics we might NOT want to push (Example) --
# Let's say we only want these logged locally but NOT sent to the gateway to save bandwidth
# To push them, simply uncomment the .register() lines below.
iteration_gauge = create_gauge('batch_job_iteration_number', 'The current loop index of the script')
sqlite_db_size = create_gauge('sqlite_db_file_size_bytes', 'The size of the SQLite DB file in bytes')

# Database operation metrics
arkiv_store_creates = create_gauge('arkiv_store_creates', 'Number of creates in db')
arkiv_store_updates = create_gauge('arkiv_store_updates', 'Number of updates in db')
arkiv_store_deletes = create_gauge('arkiv_store_deletes', 'Number of deletes in db')
arkiv_store_extends = create_gauge('arkiv_store_extends', 'Number of extends in db')
arkiv_store_ops_started = create_gauge('arkiv_store_operations_started', 'Number of started operations on db')
arkiv_store_ops_success = create_gauge('arkiv_store_operations_successful', 'Number of successful operations on db')


# --- Mapping ---
METRIC_MAP = {
    'chain_head_block': current_head_gauge,
    'arkiv_store_creates': arkiv_store_creates,
    'arkiv_store_updates': arkiv_store_updates,
    'arkiv_store_deletes': arkiv_store_deletes,
    'arkiv_store_extends': arkiv_store_extends,
    'arkiv_store_operations_started': arkiv_store_ops_started,
    'arkiv_store_operations_successful': arkiv_store_ops_success,
}

def update_geth_metrics():
    try:
        response = requests.get(GETH_METRICS_URL)
        response.raise_for_status()

        families = text_string_to_metric_families(response.text)

        for family in families:
            if family.name in METRIC_MAP:
                target_gauge = METRIC_MAP[family.name]
                if family.samples:
                    val = family.samples[0].value
                    target_gauge.set(val)

    except Exception as e:
        print(f"Error parsing metrics: {e}")

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
        await asyncio.sleep(1)

async def run_infinite_loop():
    loop_count = 0
    print(f"Starting loop. Pushing selected metrics to {GATEWAY_URL}...")

    # Background task for folder size
    asyncio.create_task(get_path_size_async_loop("l2-data/geth", arkiv_geth_db_size))

    while True:
        try:
            loop_count += 1

            # This metric is updated, but NOT pushed (because it's not in push_registry)
            iteration_gauge.set(loop_count)

            # This is updated but NOT pushed
            sqlite_db_size.set(get_file_size('l2-data/golem-base.db'))

            # This IS pushed
            sqlite_wal_size.set(get_file_size('l2-data/golem-base.db-wal'))

            # Update all Geth metrics (some might be pushed, some not, depending on registration)
            update_geth_metrics()

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