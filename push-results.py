import argparse
import json
import os
import requests


def push_results(backend_url, test_name, results_file):
    """Read a flat results JSON file and POST it wrapped in {parameters: ...}."""
    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    url = f"{backend_url}/test/{test_name}/results"
    payload = {"parameters": data}

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

    args = parser.parse_args()
    backend_url = args.url or os.getenv("TRACKER_BACKEND_URL")

    if not backend_url:
        print("Error: Backend URL must be provided via --url or TRACKER_BACKEND_URL environment variable.")
        exit(1)

    push_results(backend_url, args.test_name, args.file)
