"""Scrape op-reth Prometheus metrics and push them to InfluxDB.

op-reth does not natively support InfluxDB output (unlike op-geth, which can
push directly via ``--metrics.influxdbv2``). This script polls each configured
op-reth Prometheus endpoint on a fixed interval and forwards the samples to
InfluxDB v2. It mirrors the tagging used by op-geth's native InfluxDB output
(``test``, ``instance``, ``node``) so dashboards can be reused.

Endpoints are taken from environment variables, defaulting to the ports used
by the sequencer and validator in the Arkiv system test workflow:

* sequencer -> ``http://127.0.0.1:6160/debug/metrics/prometheus``
* validator -> ``http://127.0.0.1:6060/debug/metrics/prometheus``
"""

import math
import os
import socket
import sys
import time

import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from prometheus_client.parser import text_string_to_metric_families

# --- Configuration ---
JOB_NAME = os.getenv("JOB_NAME", "reth-metrics-job")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", socket.gethostname())
SCRAPE_INTERVAL_SECONDS = float(os.getenv("RETH_SCRAPE_INTERVAL_SECONDS", "5"))
HTTP_TIMEOUT_SECONDS = float(os.getenv("RETH_SCRAPE_HTTP_TIMEOUT_SECONDS", "5"))

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-auth-token")
INFLUX_ORG = os.getenv("INFLUXDB_ORG", "arkiv-network")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "arkiv-tests")

DEFAULT_TARGETS = {
    "sequencer": "http://127.0.0.1:6160/debug/metrics/prometheus",
    "validator": "http://127.0.0.1:6060/debug/metrics/prometheus",
}


def resolve_targets():
    """Return ``{node_name: url}`` for every reth endpoint we should scrape."""
    targets = {}
    for node, default_url in DEFAULT_TARGETS.items():
        env_name = f"RETH_{node.upper()}_METRICS_URL"
        url = os.getenv(env_name, default_url).strip()
        if url:
            targets[node] = url
    return targets


def build_points(node, prometheus_text):
    """Parse Prometheus exposition text into InfluxDB points."""
    points = []
    for family in text_string_to_metric_families(prometheus_text):
        for sample in family.samples:
            value = float(sample.value)
            if not math.isfinite(value):
                continue

            point = (
                Point(sample.name)
                .tag("test", JOB_NAME)
                .tag("instance", INSTANCE_NAME)
                .tag("node", node)
                .tag("component", "op-reth")
            )
            for label_key, label_value in sample.labels.items():
                point = point.tag(label_key, str(label_value))
            point = point.field("value", value)
            points.append(point)
    return points


def scrape_target(node, url):
    response = requests.get(url, timeout=HTTP_TIMEOUT_SECONDS)
    response.raise_for_status()
    return build_points(node, response.text)


def run(scrape_fn=scrape_target, sleep_fn=time.sleep, client_factory=None):
    """Main loop. Parameters are injected to make the loop testable."""
    targets = resolve_targets()
    if not targets:
        print("No reth metrics targets configured; exiting.", flush=True)
        return

    print(
        "Scraping reth metrics every {:.1f}s from {} -> {} "
        "(bucket={}, org={})".format(
            SCRAPE_INTERVAL_SECONDS,
            targets,
            INFLUXDB_URL,
            INFLUX_BUCKET,
            INFLUX_ORG,
        ),
        flush=True,
    )

    if client_factory is None:
        def client_factory():
            return InfluxDBClient(
                url=INFLUXDB_URL, token=INFLUX_TOKEN, org=INFLUX_ORG
            )

    with client_factory() as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        iteration = 0
        while True:
            iteration += 1
            loop_start = time.monotonic()

            for node, url in targets.items():
                try:
                    points = scrape_fn(node, url)
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"[iter {iteration}] failed to scrape {node} ({url}): {exc}",
                        flush=True,
                    )
                    continue

                if not points:
                    continue

                try:
                    write_api.write(bucket=INFLUX_BUCKET, record=points)
                    print(
                        f"[iter {iteration}] pushed {len(points)} points from {node}",
                        flush=True,
                    )
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"[iter {iteration}] failed to push {node} metrics: {exc}",
                        flush=True,
                    )

            elapsed = time.monotonic() - loop_start
            sleep_for = max(0.0, SCRAPE_INTERVAL_SECONDS - elapsed)
            sleep_fn(sleep_for)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(0)
