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

def query_database(start_time: str, end_time: str):
    """
    Queries InfluxDB with the specified start and end times and prints the results.
    """
    print(f"Querying InfluxDB from {start_time} to {end_time}...\n")

    # Construct the Flux query.
    # Note the double curly braces {{ }} in the map() function to escape them in Python f-strings.
    flux_query = f"""
    from(bucket: "arkiv-tests")
      |> range(start: {start_time}, stop: {end_time})
      |> filter(fn: (r) => r["_measurement"] == "arkiv_sqlite_db_size_bytes")
      |> filter(fn: (r) => r["job"] == "260221T095756-LocustWriteOnly-int-zeus")
      |> filter(fn: (r) => r["node_type"] == "sequencer")
      |> aggregateWindow(every: 60s, fn: last, createEmpty: false)
    """

    # Initialize the client and query the API
    with InfluxDBClient(url=INFLUXDB_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        query_api = client.query_api()

        try:
            result = query_api.query(org=INFLUX_ORG, query=flux_query)

            # Loop through the tables and records to print the results
            record_count = 0
            for table in result:
                for record in table.records:
                    record_count += 1
                    # Extracting the custom mapped fields
                    time = record["_time"]
                    field = record["_field"]
                    value = record["_value"]
                    print(f"Time: {time} | Field: {field} | Value: {value}")

            if record_count == 0:
                print("Query returned no results.")
            else:
                print(f"\nTotal records returned: {record_count}")

        except Exception as e:
            print(f"An error occurred while querying InfluxDB: {e}")

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

    args = parser.parse_args()

    query_database(args.start, args.end)