import os
import argparse
import json
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
# Update these with your actual InfluxDB connection details
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-auth-token")
INFLUX_ORG = os.getenv("INFLUXDB_ORG", "arkiv-network")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "arkiv-tests")


# "260221T102531-LocustWriteOnly-int-zeus"
def query_for_max(test_name: str, measurement: str, start_time: str, end_time: str, node_type: str):
    """
    Queries InfluxDB with the specified start and end times and prints the results.
    Returns a tuple (time, value) where time is converted to a string by the caller if needed.
    """
    print(f"Querying InfluxDB from {start_time} to {end_time} for measurement '{measurement}', node='{node_type}'...\n")

    # Construct the Flux query.
    # Note the double curly braces {{ }} in the map() function to escape them in Python f-strings.

    node_type_filter = f'|> filter(fn: (r) => r["node"] == "{node_type}")' if node_type else ""

    flux_query = f"""
    from(bucket: "arkiv-tests")
      |> range(start: {start_time}, stop: {end_time})
      |> filter(fn: (r) => r["_measurement"] == "{measurement}")
      |> filter(fn: (r) => r["test"] == "{test_name}")
      {node_type_filter}
      |> max()
    """

    # Initialize the client and query the API
    with InfluxDBClient(url=INFLUXDB_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        query_api = client.query_api()

        result = query_api.query(org=INFLUX_ORG, query=flux_query)

        # Loop through the tables and records to print the results
        time = None
        value = None
        record_count = 0
        for table in result:
            for record in table.records:
                record_count += 1
                # Extracting the custom mapped fields
                time = record["_time"]
                value = record["_value"]

        if record_count != 1:
            raise Exception(f"Expected exactly 1 record, but found {record_count} records in the result for measurement '{measurement}' and node '{node_type}'.")

        return time, value



if __name__ == "__main__":
    # Set up command-line arguments
    parser = argparse.ArgumentParser(description="Query InfluxDB with custom start and end times.")
    parser.add_argument(
        "--start",
        default="0",
        help="Start time"
    )
    parser.add_argument(
        "--end",
        default="now()",
        help="End time"
    )
    parser.add_argument(
        "--test_name",
        default="260221T102531-LocustWriteOnly-int-zeus",
        help="Test name to filter by (e.g., \"260221T102531-LocustWriteOnly-int-zeus\")"
    )

    args = parser.parse_args()

    # Helper to run a query safely and capture errors instead of crashing
    def safe_query(measurement, node_type=""):
        try:
            t, v = query_for_max(args.test_name, measurement, args.start, args.end, node_type)
            # Convert time to string so it's JSON serializable
            t_s = str(t) if t is not None else None
            return {"time": t_s, "value": v}
        except Exception as e:
            return {"time": None, "value": None, "error": str(e)}

    max_seq = safe_query("arkiv_sqlite_db_size_bytes", "sequencer")
    max_val = safe_query("arkiv_sqlite_db_size_bytes", "validator")
    max_geth_seq = safe_query("arkiv_geth_db_size", "sequencer")
    max_geth_val = safe_query("arkiv_geth_db_size", "validator")
    max_wal_seq = safe_query("arkiv_sqlite_wal_size_bytes", "sequencer")
    max_wal_val = safe_query("arkiv_sqlite_wal_size_bytes", "validator")
    max_da_data = safe_query("arkiv_da_data_size", "")

    # Build structured results
    results = {
        "sqliteDbSizeBytesSequencer": max_seq,
        "sqliteDbSizeBytesValidator": max_val,
        "gethDbSizeSequencer": max_geth_seq,
        "gethDbSizeValidator": max_geth_val,
        "sqliteWalSizeBytesSequencer": max_wal_seq,
        "sqliteWalSizeBytesValidator": max_wal_val,
        "daDataSize": max_da_data
    }

    # Print summary to stdout (best-effort)
    def print_entry(name, entry):
        if entry.get("error"):
            print(f"{name}: ERROR: {entry['error']}")
        else:
            print(f"{name}: {entry['value']} bytes at {entry['time']}")

    print_entry("Max SQLite DB Size for Sequencer", results["sqliteDbSizeBytesSequencer"])
    print_entry("Max SQLite DB Size for Validator", results["sqliteDbSizeBytesValidator"])
    print_entry("Max SQLite WAL Size for Sequencer", results["sqliteWalSizeBytesSequencer"])
    print_entry("Max SQLite WAL Size for Validator", results["sqliteWalSizeBytesValidator"])
    print_entry("Max Geth DB Size for Sequencer", results["gethDbSizeSequencer"])
    print_entry("Max Geth DB Size for Validator", results["gethDbSizeValidator"])
    print_entry("DA data size", results["daDataSize"])

    # Write results.json next to the script
    script_dir = os.path.dirname(__file__)
    out_path = os.path.join(script_dir, "results.json")

    # If a results.json already exists, read it and merge entries; otherwise write fresh.
    to_write = results
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception as e:
            print(f"Warning: failed to read existing results.json: {e}")
            existing = {}

        # Deep-merge: update nested dicts, overwrite non-dict or conflicting values with new ones
        def deep_merge(dst, src):
            for k, v in src.items():
                if k in dst and isinstance(dst[k], dict) and isinstance(v, dict):
                    deep_merge(dst[k], v)
                else:
                    dst[k] = v

        deep_merge(existing, results)
        to_write = existing

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(to_write, f, indent=2)

    print(f"\nResults written to {out_path}")
