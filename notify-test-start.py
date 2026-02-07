import requests
import argparse
import os
import json

class ParseDict(argparse.Action):
    """
    Custom argparse action to parse key=value pairs into a dictionary.
    Also handles basic type conversion for integers and booleans.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        param_dict = {}
        for item in values:
            if '=' not in item:
                # Handle flags without values as boolean True
                param_dict[item] = True
                continue

            key, value = item.split("=", 1)

            # Type Casting: Try to convert to int or bool
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.isdigit():
                value = int(value)

            param_dict[key] = value

        setattr(namespace, self.dest, param_dict)

def create_test(backend_url, parameters):
    # Construct the full endpoint URL
    url = f"{backend_url}/test/new"

    # Define the payload
    payload = {
        "name": "",
        "params": json.dumps(parameters),
    }

    print(f"Sending request to: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    response = requests.post(url, json=payload)
    response.raise_for_status()

    print(f"\n✅ Success! Status Code: {response.status_code}")
    print("Response Body:", response.json())
    name = response.json().get("name")
    with open("test-name.txt") as f:
        f.write(name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send a POST request with structured parameters to the Tracker Backend."
    )

    # Arguments
    parser.add_argument(
        "--url",
        help="The backend URL (defaults to TRACKER_BACKEND_URL env var)"
    )
    parser.add_argument(
        "--parameters",
        required=True,
        nargs='+',
        action=ParseDict,
        help="Parameters in key=value format (e.g., env=prod retries=3 debug=true)"
    )

    args = parser.parse_args()

    # Prioritize the command line argument, fallback to environment variable
    backend_url = args.url or os.getenv("TRACKER_BACKEND_URL")

    if not backend_url:
        print("Error: Backend URL must be provided via --url or TRACKER_BACKEND_URL environment variable.")
    else:
        create_test(backend_url, args.name, args.parameters)