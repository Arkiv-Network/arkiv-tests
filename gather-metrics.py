import asyncio
import os
import socket
from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

# --- Configuration ---
JOB_NAME = os.getenv('JOB_NAME', 'geth-metrics-job')
INSTANCE_NAME = os.getenv('INSTANCE_NAME', socket.gethostname())

# InfluxDB v2 specifics
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-super-secret-auth-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "arkiv-network")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "arkiv-tests")

# --- State Management ---
# Since we don't have Prometheus 'Gauge' objects holding state anymore,
# we'll use a simple dictionary to hold the latest metric values.
metrics_state = {
    'batch_job_iteration_number': 0,
    'arkiv_free_space': 0,
    'arkiv_used_space': 0,
    'arkiv_da_data_size': 0,
    'arkiv_geth_db_size': {'sequencer': 0, 'validator': 0},
    'arkiv_sqlite_db_size_bytes': {'sequencer': 0, 'validator': 0},
    'arkiv_sqlite_wal_size_bytes': {'sequencer': 0, 'validator': 0},
}

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
        'df', '/',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode == 0:
        lines = stdout.decode().strip().split('\n')
        data_line = lines[1].split()

        used_kb = int(data_line[2])
        available_kb = int(data_line[3])
        return available_kb * 1024, used_kb * 1024
    else:
        raise RuntimeError(f"df command failed: {stderr.decode()}")

async def get_free_space_async_loop():
    while True:
        free, taken = await get_free_disk_space()
        if free < 1000000000:
            # @todo implement panic stop whole test to prevent machine
            pass

        metrics_state['arkiv_free_space'] = free
        metrics_state['arkiv_used_space'] = taken
        await asyncio.sleep(1)

async def run_infinite_loop():
    loop_count = 0
    print(f"Starting loop. Pushing selected metrics to InfluxDB at {INFLUXDB_URL}...")

    # Background task for folder size
    asyncio.create_task(get_path_size_async_loop("sequencer-data/geth", "arkiv_geth_db_size", "sequencer"))
    asyncio.create_task(get_path_size_async_loop("validator-data/geth", "arkiv_geth_db_size", "validator"))
    asyncio.create_task(get_path_size_async_loop("da-data", "arkiv_da_data_size"))
    asyncio.create_task(get_free_space_async_loop())

    # Initialize the Async InfluxDB Client
    async with InfluxDBClientAsync(url=INFLUXDB_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        write_api = client.write_api()

        while True:
            try:
                loop_count += 1
                metrics_state['batch_job_iteration_number'] = loop_count

                # Update SQLite file sizes directly in the state
                metrics_state['arkiv_sqlite_db_size_bytes']['sequencer'] = get_file_size('sequencer-data/golem-base.db')
                metrics_state['arkiv_sqlite_wal_size_bytes']['sequencer'] = get_file_size('sequencer-data/golem-base.db-wal')

                metrics_state['arkiv_sqlite_db_size_bytes']['validator'] = get_file_size('validator-data/golem-base.db')
                metrics_state['arkiv_sqlite_wal_size_bytes']['validator'] = get_file_size('validator-data/golem-base.db-wal')

                # --- Build InfluxDB Points ---
                points = []

                # Helper function to mimic Prometheus logic (Measurement Name -> value, plus tags)
                def create_point(measurement, value, node_type=None):
                    p = Point(measurement).tag("job", JOB_NAME).tag("instance", INSTANCE_NAME)
                    if node_type:
                        p.tag("node_type", node_type)
                    # Field name "value" is a standard convention for single-value metrics
                    return p.field("value", float(value))

                    # Translate our state dictionary into InfluxDB Points
                for key, val in metrics_state.items():
                    if isinstance(val, dict):
                        for node_type, size in val.items():
                            points.append(create_point(key, size, node_type))
                    else:
                        points.append(create_point(key, val))

                # --- Push to InfluxDB ---
                await write_api.write(bucket=INFLUX_BUCKET, record=points)

                print(f"Pushed iteration: {loop_count}")
                await asyncio.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(run_infinite_loop())