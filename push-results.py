import argparse
import json
import os
from decimal import Decimal

import requests

try:
    from influxdb_client import InfluxDBClient
except ImportError:  # pragma: no cover - exercised in unit tests via patching
    InfluxDBClient = None


INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-auth-token")
INFLUX_ORG = os.getenv("INFLUXDB_ORG", "arkiv-network")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "arkiv-tests")


def wei_to_eth_str(wei):
    """Format a Wei amount as an ETH string with magnitude-based precision and sign preservation."""
    if wei < 0:
        return f"-{wei_to_eth_str(-wei)}"

    val = Decimal(wei) / Decimal(10**18)
    if val > 100:
        return f"{val:.2f}"
    if val > 10:
        return f"{val:.3f}"
    if val > 1:
        return f"{val:.4f}"
    if val > Decimal("0.1"):
        return f"{val:.5f}"
    if val > Decimal("0.01"):
        return f"{val:.6f}"
    if val > Decimal("0.001"):
        return f"{val:.7f}"
    return f"{val:f}"


def escape_flux_string(value):
    """Escape a string value before interpolating it into a Flux query."""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def query_last_metric_total(test_name, measurement):
    """Return the latest total value for a metric in InfluxDB, or None if unavailable."""
    if InfluxDBClient is None:
        return None

    escaped_bucket = escape_flux_string(INFLUX_BUCKET)
    escaped_measurement = escape_flux_string(measurement)
    escaped_test_name = escape_flux_string(test_name)

    flux_query = f"""
    from(bucket: "{escaped_bucket}")
      |> range(start: 0)
      |> filter(fn: (r) => r["_measurement"] == "{escaped_measurement}")
      |> filter(fn: (r) => r["test"] == "{escaped_test_name}")
      |> last()
      |> group()
      |> sum()
    """

    try:
        with InfluxDBClient(
            url=INFLUXDB_URL, token=INFLUX_TOKEN, org=INFLUX_ORG
        ) as client:
            query_api = client.query_api()
            result = query_api.query(org=INFLUX_ORG, query=flux_query)
    except Exception as exc:
        raise RuntimeError(
            f"Unable to query InfluxDB for measurement {measurement!r} and test {test_name!r}"
        ) from exc

    value = None
    for table in result:
        for record in table.records:
            value = record["_value"]

    return value


def collect_l1_result_metrics(test_name):
    """Collect optional L1 result metrics for the tracker payload."""
    try:
        transactions_total = query_last_metric_total(test_name, "arkiv_l1_transactions_total")
        simulated_spend_wei = query_last_metric_total(test_name, "arkiv_mainnet_gas_price")
    except RuntimeError as exc:
        print(f"Warning: unable to fetch optional L1 metrics from InfluxDB: {exc}")
        return {}

    result_metrics = {}
    if transactions_total is not None:
        result_metrics["totalTransactionsL1"] = {"value": int(transactions_total)}

    if simulated_spend_wei is not None:
        estimated_spend_wei = int(simulated_spend_wei)
        result_metrics["gasSpentL1"] = {
            "value": estimated_spend_wei,
            "display": wei_to_eth_str(estimated_spend_wei),
        }

    return result_metrics


def push_results(backend_url, test_name, results_file, seconds):
    """Read a flat results JSON file and POST it wrapped in {parameters: ...}."""
    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    data.update(collect_l1_result_metrics(test_name))

    url = f"{backend_url}/test/{test_name}/results"
    payload = {"parameters": data, "seconds": seconds}

    print(f"Posting results to: {url}")
    response = requests.post(url, json=payload)
    response.raise_for_status()
    print(f"✅ Success! Status Code: {response.status_code}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Push a results JSON file to the tracker backend /test/:name/results endpoint."
    )
    parser.add_argument("--url", help="Backend URL (defaults to TRACKER_BACKEND_URL env var)")
    parser.add_argument("--test-name", required=True, help="Test name")
    parser.add_argument("--file", required=True, help="Path to the results JSON file")
    parser.add_argument("--seconds", type=int, required=True, help="How much time passed in tests")

    args = parser.parse_args()
    backend_url = args.url or os.getenv("TRACKER_BACKEND_URL")

    if not backend_url:
        print("Error: Backend URL must be provided via --url or TRACKER_BACKEND_URL environment variable.")
        exit(1)

    push_results(backend_url, args.test_name, args.file, args.seconds)
