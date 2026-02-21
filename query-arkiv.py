import os
import argparse
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
    """
    print(f"Querying InfluxDB from {start_time} to {end_time}...\n")

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
            raise Exception(f"Expected no records, but found {record_count} records in the result.")

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

    max_seq = query_for_max(args.test_name, "arkiv_sqlite_db_size_bytes", args.start, args.end, "sequencer")
    max_val = query_for_max(args.test_name, "arkiv_sqlite_db_size_bytes", args.start, args.end, "validator")
    max_geth_seq = query_for_max(args.test_name, "arkiv_geth_db_size", args.start, args.end, "sequencer")
    max_geth_val = query_for_max(args.test_name, "arkiv_geth_db_size", args.start, args.end, "validator")
    max_wal_seq = query_for_max(args.test_name, "arkiv_sqlite_wal_size_bytes", args.start, args.end, "sequencer")
    max_wal_val = query_for_max(args.test_name, "arkiv_sqlite_wal_size_bytes", args.start, args.end, "validator")
    max_da_data = query_for_max(args.test_name, "arkiv_da_data_size_bytes", args.start, args.end, "")

    print(f"Max SQLite DB Size for Sequencer: {max_seq[1]} bytes at {max_seq[0]}")
    print(f"Max SQLite DB Size for Validator: {max_val[1]} bytes at {max_val[0]}")
    print(f"Max SQLite WAL Size for Sequencer: {max_wal_seq[1]} bytes at {max_wal_seq[0]}")
    print(f"Max SQLite WAL Size for Validator: {max_wal_val[1]} bytes at {max_wal_val[0]}")
    print(f"Max Geth DB Size for Sequencer: {max_geth_seq[1]} bytes at {max_geth_seq[0]}")
    print(f"Max Geth DB Size for Validator: {max_geth_val[1]} bytes at {max_geth_val[0]}")
    print(f"Da size max at {max_wal_val[0]} is {max_da_data[1]} bytes")