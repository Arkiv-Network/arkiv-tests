import os

import requests
import time
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

registry = CollectorRegistry()

current_head_gauge = Gauge(
    'chain_head_block_number',
    'The current chain head block number from Geth',
    [],
    registry=registry
)

sqlite_wal_size = Gauge(
    'sqlite_wal_file_size_bytes',
    'The size of the SQLite WAL file in bytes',
    [],
    registry=registry
)
sqlite_db_size = Gauge(
    'sqlite_db_file_size_bytes',
    'The size of the SQLite DB file in bytes',
    [],
    registry=registry
)


JOB_NAME = os.getenv('PROMETHEUS_JOB_NAME', 'geth-metrics-job')

def get_all_geth_metrics(host="127.0.0.1", port=6060):
    url = f"http://{host}:{port}/debug/metrics/prometheus"

    try:
        response = requests.get(url)
        response.raise_for_status()

        # Split by newline and filter out comments (lines starting with #)
        metrics = [line for line in response.text.split('\n') if line and not line.startswith('#')]

        print(f"--- Found {len(metrics)} active metrics ---\n")
        for m in metrics:
            if m.startswith("chain_head_block"):
                chain_head_block = m.split(' ')[1]
                print(f"Chain Head Block: {chain_head_block}")
                current_head_gauge.set(int(chain_head_block))

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Geth metrics: {e}")
        print("Ensure Geth is running with: --metrics --metrics.addr 127.0.0.1")

def get_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except OSError as e:
        print(f"Error getting file size for {file_path}: {e}")
        return -1

def run_infinite_loop():
    # 1. Create a registry

    # 2. Define a Gauge to track the loop iteration
    # Labels allow you to filter data easily in Grafana/Prometheus
    iteration_gauge = Gauge(
        'batch_job_iteration_number',
        'The current loop index of the script',
        [], # Example label
        registry=registry
    )

    loop_count = 0
    gateway_url = 'https://l2.arkiv-global.net/eKUSzE1KvC'

    print(f"Starting loop. Pushing to {gateway_url}...")

    while True:
        try:
            loop_count += 1

            # 3. Update the metric value
            iteration_gauge.set(loop_count)

            sqlite_db_size.set(get_file_size('l2-data/golem-base.db'))
            sqlite_wal_size.set(get_file_size('l2-data/golem-base.db-wal'))

            get_all_geth_metrics()
            # 4. Push to the Gateway
            # We use the same job name so the metric is overwritten/updated each time
            push_to_gateway(gateway_url, job=JOB_NAME, registry=registry)

            print(f"Pushed iteration: {loop_count}")

            # Wait 5 seconds before next push
            time.sleep(1)

        except KeyboardInterrupt:
            print("\nScript stopped by user.")
            break
        except Exception as e:
            print(f"An error occurred: {e}, retrying in 10 seconds...")
            time.sleep(10)
            continue

if __name__ == "__main__":
    run_infinite_loop()

if __name__ == "__main__":
    get_all_geth_metrics()