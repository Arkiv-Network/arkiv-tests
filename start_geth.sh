#!/usr/bin/env bash

set -x

./geth \
    --dev \
    --http \
    --http.api 'eth,web3,net,debug,arkiv' \
    --verbosity 3 \
    --http.addr '0.0.0.0' \
    --http.port 8545 \
    --http.corsdomain '*' \
    --http.vhosts '*' \
    --ws --ws.addr '0.0.0.0' --ws.port 8545 \
    --datadir ./golembase_sqlite&

# Wait for geth to start
echo "Waiting for Geth HTTP API to be ready..."

# Set timeout variables
MAX_RETRIES=20
counter=0

while [ $counter -lt $MAX_RETRIES ]; do
    # Try to fetch the latest block number.
    # We send output to /dev/null and check the exit status of curl.
    if curl -s -X POST -H "Content-Type: application/json" \
        --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
        http://127.0.0.1:8545 > /dev/null; then
        echo "Geth is up and running!"
        break
    fi

    echo "Waiting for Geth... $((counter+1))/$MAX_RETRIES"
    sleep 1
    counter=$((counter+1))
done

# Check if we timed out
if [ $counter -eq $MAX_RETRIES ]; then
    echo "Error: Geth HTTP API did not become available within 20 seconds."
    exit 1
fi