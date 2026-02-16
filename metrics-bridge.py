import os
import requests
import time

GETH_METRICS_URL = os.getenv("METRICS_URL")
PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL")
INTERVAL = int(os.getenv("PUSH_INTERVAL", 1))

def push_metrics():
    try:
        # 1. Scrape Geth
        response = requests.get(GETH_METRICS_URL)
        response.raise_for_status()

        # 2. Push to Gateway
        push_res = requests.post(PUSHGATEWAY_URL, data=response.text)
        push_res.raise_for_status()
        print(f"Metrics pushed successfully at {time.ctime()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    while True:
        push_metrics()
        time.sleep(INTERVAL)