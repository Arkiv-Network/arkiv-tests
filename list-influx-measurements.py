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


# Utility: list measurements (metrics) in a bucket
def list_measurements():
    """Connect to InfluxDB and print a JSON array of measurements found in the bucket.

    Parameters are optional and will fall back to the environment-configured values.
    The function handles connection errors and prints a helpful message instead of raising.
    """
    url = INFLUXDB_URL
    token = INFLUX_TOKEN
    org = INFLUX_ORG
    bucket = INFLUX_BUCKET

    flux = f'import "influxdata/influxdb/schema"\nschema.measurements(bucket: "{bucket}")'

    try:
        client = InfluxDBClient(url=url, token=token, org=org)
        query_api = client.query_api()
        tables = query_api.query(flux)

        measurements = []
        for table in tables:
            for record in table.records:
                # record.get_value() returns the measurement name
                measurements.append(record.get_value())

        measurements = sorted(set(measurements))
        print(json.dumps(measurements, indent=2))
        return measurements

    except Exception as e:
        print("Failed to list measurements from InfluxDB.")
        print(f"URL: {url}")
        print("Error:", str(e))
        return None


# Keep the original query() placeholder but make it safe/complete if needed later.
def query(start_time=None, end_time=None, measurement=None, test_name=None, node_type=None):
    """
    Queries InfluxDB with the specified start and end times and prints the results.
    Returns a tuple (time, value) where time is converted to a string by the caller if needed.

    This function was a placeholder in the original file. It's left here to avoid breaking imports
    and can be extended later. For now it raises NotImplementedError to make its status explicit.
    """
    raise NotImplementedError("The query() helper is not implemented in this script. Use the CLI subcommands.")


if __name__ == "__main__":
    list_measurements()
