import asyncio
import json
import math
import os
import socket

import requests
from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from prometheus_client.parser import text_string_to_metric_families

# --- Configuration ---
JOB_NAME = os.getenv("JOB_NAME", "geth-metrics-job")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", socket.gethostname())
PUSH_INTERVAL_SECONDS = float(os.getenv("METRICS_PUSH_INTERVAL_SECONDS", "1"))
CELESTIA_ADDRESS = os.getenv("CELESTIA_ADDRESS", "").strip()
CELESTIA_RPC_ADDR = os.getenv("CELESTIA_RPC_ADDR", "").strip()
OP_NODE_L1_RPC_URL = os.getenv("OP_NODE_L1_RPC_URL", "").strip()
OP_NODE_L1_ADDRESS = os.getenv("OP_NODE_L1_ADDRESS", "").strip()
OP_BATCHER_L1_ADDRESS = os.getenv("OP_BATCHER_L1_ADDRESS", "").strip()
OP_PROPOSER_L1_ADDRESS = os.getenv("OP_PROPOSER_L1_ADDRESS", "").strip()
OP_NODE_L1_START_BLOCK = max(int(os.getenv("OP_NODE_L1_START_BLOCK", "0")), 0)
MAX_L1_LOGGED_SENDERS = 5
GAS_BASE_NETWORK = os.getenv(
    "GAS_BASE_NETWORK", "https://mainnet.rpc-node.dev.golem.network/"
).strip()
CELENIUM_API_URL = os.getenv(
    "CELENIUM_API_URL", "https://api-mainnet.celenium.io"
).strip()

SCRAPE_TARGETS = {
    "op-batcher": os.getenv(
        "OP_BATCHER_METRICS_URL", "http://127.0.0.1:7365/metrics"
    ),
    "op-proposer": os.getenv(
        "OP_PROPOSER_METRICS_URL", "http://127.0.0.1:7375/metrics"
    ),
}

# InfluxDB v2 specifics
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-auth-token")
INFLUX_ORG = os.getenv("INFLUXDB_ORG", "arkiv-network")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "arkiv-tests")

# --- State Management ---
# Since we don't have Prometheus 'Gauge' objects holding state anymore,
# we'll use a simple dictionary to hold the latest metric values.
metrics_state = {
    "batch_job_iteration_number": 0,
    "arkiv_free_space": 0,
    "arkiv_used_space": 0,
    "arkiv_da_data_size": 0,
    "arkiv_geth_db_size": {"sequencer": 0, "validator": 0},
    "arkiv_sqlite_db_size_bytes": {"sequencer": 0, "validator": 0},
    "arkiv_pebble_db_size": {"sequencer": 0, "validator": 0},
    "arkiv_sqlite_wal_size_bytes": {"sequencer": 0, "validator": 0},
}
l1_tx_metrics_state = {
    "last_scanned_block": None,
    "transactions_total": {},
    "gas_used_total": {},
    "simulated_mainnet_spending": {},
    "simulated_eth_spend_wei_total": 0,
}
da_metrics_state = {
    "last_da_data_size": 0,
    "simulated_da_spending_total": 0.0,
}


def get_point_measurement(point):
    return getattr(point, "measurement", "")


def escape_log_value(value):
    return str(value).replace("\\", "\\\\").replace(",", "\\,").replace("=", "\\=")


def format_log_mapping(mapping):
    if not mapping:
        return "-"

    return ",".join(
        f"{escape_log_value(key)}={escape_log_value(mapping[key])}"
        for key in sorted(mapping)
    )


def format_seen_senders(senders):
    if not senders:
        return "none"

    visible_senders = senders[:MAX_L1_LOGGED_SENDERS]
    hidden_sender_count = len(senders) - len(visible_senders)
    formatted_senders = ", ".join(visible_senders)
    if hidden_sender_count > 0:
        return f"{formatted_senders}, ... (+{hidden_sender_count} more)"

    return formatted_senders


def describe_point_for_log(point):
    measurement = get_point_measurement(point) or "<unknown>"
    tags = getattr(point, "tags", {})
    fields = getattr(point, "fields", {})
    warnings = []

    if not hasattr(point, "measurement"):
        warnings.append("missing_measurement")
    if not isinstance(tags, dict):
        warnings.append("invalid_tags")
        tags = {}
    if not isinstance(fields, dict):
        warnings.append("invalid_fields")
        fields = {}

    warning_suffix = ""
    if warnings:
        warning_suffix = f" warnings[{','.join(warnings)}]"
    return (
        f"{measurement} tags[{format_log_mapping(tags)}] "
        f"fields[{format_log_mapping(fields)}]{warning_suffix}"
    )


def log_prepared_l1_points(loop_count, points):
    l1_points = [
        point for point in points if get_point_measurement(point).startswith("arkiv_l1_")
    ]
    if not l1_points:
        return

    measurement_counts = {}
    for point in l1_points:
        measurement = get_point_measurement(point)
        measurement_counts[measurement] = measurement_counts.get(measurement, 0) + 1

    print(
        f"[l1-tracker] iteration {loop_count}: prepared {len(l1_points)} L1 point(s) "
        f"for InfluxDB write. measurements={format_log_mapping(measurement_counts)}"
    )
    for point in l1_points:
        print(
            f"[l1-tracker] iteration {loop_count}: queued {describe_point_for_log(point)}"
        )


def normalize_eth_address(address):
    if not isinstance(address, str):
        return ""

    address = address.strip().lower()
    if not address.startswith("0x"):
        return ""

    return address


def hex_to_int(value):
    if value is None:
        return 0

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        if value.startswith("0x"):
            return int(value, 16)
        return int(value)

    raise TypeError(f"Unsupported type for hex_to_int conversion: {type(value)!r}")


def get_tracked_l1_senders():
    tracked_senders = {}
    op_node_address = normalize_eth_address(OP_NODE_L1_ADDRESS)
    if op_node_address:
        tracked_senders["op-node"] = op_node_address

    op_batcher_address = normalize_eth_address(OP_BATCHER_L1_ADDRESS)
    if op_batcher_address:
        tracked_senders["op-batcher"] = op_batcher_address

    op_proposer_address = normalize_eth_address(OP_PROPOSER_L1_ADDRESS)
    if op_proposer_address:
        tracked_senders["op-proposer"] = op_proposer_address

    return tracked_senders


def get_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


async def get_path_size_async(path):
    if not os.path.isdir(path):
        return 0

    process = await asyncio.create_subprocess_exec(
        "du",
        "-sb",
        path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    return int(stdout.split()[0]) if process.returncode == 0 else 0


async def get_path_size_async_loop(path, metric_key, node_type=None):
    while True:
        size = await get_path_size_async(path)

        # Update the state dictionary instead of a Prometheus Gauge
        if node_type:
            metrics_state[metric_key][node_type] = size
        else:
            metrics_state[metric_key] = size

        if size < 100000000:
            await asyncio.sleep(1)
        else:
            await asyncio.sleep(10)


async def get_free_disk_space():
    proc = await asyncio.create_subprocess_exec(
        "df",
        "/",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode == 0:
        lines = stdout.decode().strip().split("\n")
        data_line = lines[1].split()

        used_kb = int(data_line[2])
        available_kb = int(data_line[3])
        return available_kb * 1024, used_kb * 1024

    raise RuntimeError(f"df command failed: {stderr.decode()}")


async def get_free_space_async_loop():
    while True:
        free, taken = await get_free_disk_space()
        if free < 1000000000:
            # @todo implement panic stop whole test to prevent machine
            pass

        metrics_state["arkiv_free_space"] = free
        metrics_state["arkiv_used_space"] = taken
        await asyncio.sleep(1)



def create_point(measurement, value, tags=None):
    point = Point(measurement).tag("test", JOB_NAME).tag("instance", INSTANCE_NAME)
    for tag_key, tag_value in (tags or {}).items():
        point = point.tag(tag_key, str(tag_value))

    # Field name "value" is a standard convention for single-value metrics
    return point.field("value", float(value))


def call_json_rpc(url, method, params):
    try:
        response = requests.post(
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params,
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Unable to call {method} on {url}") from exc

    payload = response.json()
    error = payload.get("error")
    if error:
        raise RuntimeError(f"RPC {method} failed: {error}")

    return payload.get("result")


def get_receipts_for_block(url, block_number, transaction_hashes):
    try:
        receipts = call_json_rpc(url, "eth_getBlockReceipts", [hex(block_number)])
        if isinstance(receipts, list):
            return {
                receipt.get("transactionHash"): receipt
                for receipt in receipts
                if receipt.get("transactionHash")
            }
    except RuntimeError as exc:
        print(
            "eth_getBlockReceipts unavailable for "
            f"block {block_number}, falling back to per-transaction receipts: {exc}"
        )

    return {
        tx_hash: call_json_rpc(url, "eth_getTransactionReceipt", [tx_hash])
        for tx_hash in transaction_hashes
    }


def get_next_l1_block_to_scan():
    last_scanned_block = l1_tx_metrics_state["last_scanned_block"]
    if last_scanned_block is None:
        return OP_NODE_L1_START_BLOCK

    return last_scanned_block + 1


def find_matching_l1_transactions(transactions, tracked_senders):
    matching_transactions = []
    seen_senders = []
    seen_sender_set = set()

    for transaction in transactions:
        tx_hash = transaction.get("hash")
        if not tx_hash:
            continue

        sender = normalize_eth_address(transaction.get("from"))
        if sender and sender not in seen_sender_set:
            seen_sender_set.add(sender)
            seen_senders.append(sender)

        match = next(
            (
                (tracked_component, tracked_sender)
                for tracked_component, tracked_sender in tracked_senders.items()
                if sender == tracked_sender
            ),
            None,
        )
        if match:
            component, tracked_sender = match
            matching_transactions.append((component, tracked_sender, transaction))

    return matching_transactions, seen_senders


def increment_l1_sender_totals(component, gas_used):
    l1_tx_metrics_state["transactions_total"][component] = (
        l1_tx_metrics_state["transactions_total"].get(component, 0) + 1
    )
    l1_tx_metrics_state["gas_used_total"][component] = (
        l1_tx_metrics_state["gas_used_total"].get(component, 0) + gas_used
    )


def increment_l1_simulated_gas_usage_total(component, gas_used, gas_price_wei):
    if gas_price_wei is None:
        return

    simulated_mainnet_spending = l1_tx_metrics_state.setdefault(
        "simulated_mainnet_spending", {}
    )
    simulated_spending_wei = gas_used * gas_price_wei
    simulated_mainnet_spending[component] = (
        simulated_mainnet_spending.get(component, 0) + simulated_spending_wei
    )
    l1_tx_metrics_state["simulated_eth_spend_wei_total"] = (
        l1_tx_metrics_state.get("simulated_eth_spend_wei_total", 0)
        + simulated_spending_wei
    )


def build_l1_sender_total_points(tracked_senders):
    points = []
    last_scanned_block = l1_tx_metrics_state["last_scanned_block"]
    if last_scanned_block is None:
        last_scanned_block = OP_NODE_L1_START_BLOCK

    for component, tracked_sender in tracked_senders.items():
        transaction_total = l1_tx_metrics_state["transactions_total"].get(component, 0)
        gas_used_total = l1_tx_metrics_state["gas_used_total"].get(component, 0)
        common_tags = {"component": component, "sender": tracked_sender}

        transactions_total_point = create_point(
            "arkiv_l1_transactions_total",
            transaction_total,
            common_tags,
        )
        gas_used_total_point = create_point(
            "arkiv_l1_gas_used_total",
            gas_used_total,
            common_tags,
        )
        last_scanned_block_point = create_point(
            "arkiv_l1_last_scanned_block",
            last_scanned_block,
            common_tags,
        )
        points.extend(
            [transactions_total_point, gas_used_total_point, last_scanned_block_point]
        )
        print(
            f"[l1-tracker] component={component}: totals transaction_count={transaction_total} "
            f"gas_used_total={gas_used_total} last_scanned_block={last_scanned_block}"
        )
        print(
            f"[l1-tracker] queued {describe_point_for_log(transactions_total_point)}"
        )
        print(f"[l1-tracker] queued {describe_point_for_log(gas_used_total_point)}")
        print(
            f"[l1-tracker] queued {describe_point_for_log(last_scanned_block_point)}"
        )

    return points


def build_simulated_mainnet_spending_points():
    points = []
    total_simulated_spend_wei = l1_tx_metrics_state.get("simulated_eth_spend_wei_total", 0)
    simulated_mainnet_spending = l1_tx_metrics_state.get("simulated_mainnet_spending", {})

    for component, simulated_spending_wei in simulated_mainnet_spending.items():
        points.append(
            create_point(
                "arkiv_simulated_mainnet_spending",
                simulated_spending_wei,
                {"component": component},
            )
        )

    if total_simulated_spend_wei:
        points.append(
            create_point("arkiv_simulated_eth_spend", total_simulated_spend_wei / 1e18, {})
        )

    return points


def fetch_celenium_gas_price():
    try:
        response = requests.get(
            f"{CELENIUM_API_URL}/v1/gas/price", timeout=10
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Unable to fetch gas price from {CELENIUM_API_URL}"
        ) from exc

    data = response.json()
    return float(data["median"])


def fetch_celenium_pfb_estimate(size):
    try:
        response = requests.get(
            f"{CELENIUM_API_URL}/v1/gas/estimate_for_pfb",
            params={"sizes": size},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Unable to fetch PFB estimate from {CELENIUM_API_URL}"
        ) from exc

    data = response.json()
    if isinstance(data, list):
        return int(data[0]) if data else 0
    return int(data)


def collect_celestia_da_gas_metrics_sync():
    if not CELENIUM_API_URL:
        return []

    current_da_size = metrics_state.get("arkiv_da_data_size", 0)
    last_da_size = da_metrics_state["last_da_data_size"]

    gas_price = fetch_celenium_gas_price()
    points = [create_point("arkiv_celestia_gas_price", gas_price)]

    da_diff = current_da_size - last_da_size
    if da_diff > 0:
        da_metrics_state["last_da_data_size"] = current_da_size
        estimate = fetch_celenium_pfb_estimate(da_diff)
        da_metrics_state["simulated_da_spending_total"] += estimate * gas_price

    if da_metrics_state["simulated_da_spending_total"]:
        points.append(
            create_point(
                "arkiv_simulated_da_spending",
                da_metrics_state["simulated_da_spending_total"],
            )
        )

    return points


async def collect_celestia_balance_points():
    if not CELESTIA_ADDRESS or not CELESTIA_RPC_ADDR:
        return []

    process = await asyncio.create_subprocess_exec(
        "celestia-appd",
        "query",
        "bank",
        "balances",
        CELESTIA_ADDRESS,
        "--node",
        CELESTIA_RPC_ADDR,
        "--output",
        "json",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(
            "Unable to fetch Celestia account balance: "
            f"{stderr.decode().strip() or stdout.decode().strip()}"
        )

    response = json.loads(stdout)
    utia_balance = 0
    for balance in response.get("balances", []):
        if balance.get("denom") == "utia":
            utia_balance = int(balance.get("amount", 0))
            break

    return [
        create_point(
            "arkiv_celestia_account_balance",
            utia_balance,
            {"address": CELESTIA_ADDRESS, "denom": "utia"},
        )
    ]


def scrape_prometheus_target(target_name, url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Unable to fetch Prometheus metrics for {target_name} from {url}"
        ) from exc

    points = []
    for family in text_string_to_metric_families(response.text):
        for sample in family.samples:
            value = float(sample.value)
            if not math.isfinite(value):
                continue

            sample_tags = {"component": target_name}
            sample_tags.update(sample.labels)
            points.append(create_point(sample.name, value, sample_tags))

    return points


async def collect_scraped_metrics_points():
    scrape_target_items = [
        (target_name, url)
        for target_name, url in SCRAPE_TARGETS.items()
        if url and url.strip()
    ]
    if not scrape_target_items:
        return []

    results = await asyncio.gather(
        *[
            asyncio.to_thread(scrape_prometheus_target, target_name, url)
            for target_name, url in scrape_target_items
        ],
        return_exceptions=True,
    )

    points = []
    for (target_name, _), result in zip(scrape_target_items, results, strict=True):
        if isinstance(result, Exception):
            print(f"Failed to scrape {target_name} metrics: {result}")
            continue

        points.extend(result)

    return points


def collect_l1_sender_points_sync():
    tracked_senders = get_tracked_l1_senders()
    if not OP_NODE_L1_RPC_URL or not tracked_senders:
        return []

    latest_block = hex_to_int(call_json_rpc(OP_NODE_L1_RPC_URL, "eth_blockNumber", []))
    next_block = get_next_l1_block_to_scan()
    new_points = []
    gas_price_wei = None
    tracked_sender_summary = ", ".join(
        f"{component}={tracked_sender}"
        for component, tracked_sender in sorted(tracked_senders.items())
    )
    scanned_blocks = 0
    matched_transactions_total = 0

    for block_number in range(next_block, latest_block + 1):
        block = call_json_rpc(
            OP_NODE_L1_RPC_URL,
            "eth_getBlockByNumber",
            [hex(block_number), True],
        )
        scanned_blocks += 1
        transactions = block.get("transactions", [])
        matching_transactions, seen_senders = find_matching_l1_transactions(
            transactions, tracked_senders
        )

        if matching_transactions:
            matched_transactions_total += len(matching_transactions)
            print(
                f"[l1-tracker] block {block_number}: matched {len(matching_transactions)} "
                f"transaction(s) for {', '.join(component for component, _, _ in matching_transactions)}"
            )
            print(
                f"[l1-tracker] block {block_number}: fetching receipts for "
                f"{', '.join(transaction['hash'] for _, _, transaction in matching_transactions)}"
            )
        elif transactions:
            print(
                f"[l1-tracker] block {block_number}: scanned {len(transactions)} transaction(s) "
                f"but found no matches. tracked={tracked_sender_summary}; "
                f"seen_from={format_seen_senders(seen_senders)}"
            )

        receipts_by_hash = {}
        if matching_transactions:
            receipts_by_hash = get_receipts_for_block(
                OP_NODE_L1_RPC_URL,
                block_number,
                [transaction["hash"] for _, _, transaction in matching_transactions],
            )

        for component, tracked_sender, transaction in matching_transactions:
            receipt = receipts_by_hash.get(transaction["hash"], {})
            gas_used = hex_to_int(receipt.get("gasUsed"))
            increment_l1_sender_totals(component, gas_used)
            if gas_price_wei is None and GAS_BASE_NETWORK:
                gas_price_wei = hex_to_int(
                    call_json_rpc(GAS_BASE_NETWORK, "eth_gasPrice", [])
                )
            increment_l1_simulated_gas_usage_total(component, gas_used, gas_price_wei)
            point = create_point(
                "arkiv_l1_transaction_gas_used",
                gas_used,
                {
                    "component": component,
                    "sender": tracked_sender,
                    "tx_hash": transaction["hash"],
                    "block_number": block_number,
                    "to": transaction.get("to") or "",
                },
            )
            new_points.append(point)
            print(
                f"[l1-tracker] tx {transaction['hash']}: component={component} "
                f"sender={tracked_sender} to={transaction.get('to') or ''} gas_used={gas_used} "
                f"cumulative_transactions={l1_tx_metrics_state['transactions_total'][component]} "
                f"cumulative_gas_used={l1_tx_metrics_state['gas_used_total'][component]}"
            )
            print(f"[l1-tracker] queued {describe_point_for_log(point)}")

        l1_tx_metrics_state["last_scanned_block"] = block_number

    if scanned_blocks:
        cumulative_totals_summary = ", ".join(
            f"{component}={l1_tx_metrics_state['transactions_total'].get(component, 0)}"
            for component in sorted(tracked_senders)
        )
        print(
            f"[l1-tracker] scanned {scanned_blocks} block(s) from {next_block} to {latest_block}; "
            f"matched {matched_transactions_total} tracked transaction(s). "
            f"tracked={tracked_sender_summary}; totals={cumulative_totals_summary}"
        )

    new_points.extend(build_l1_sender_total_points(tracked_senders))

    return new_points


def collect_mainnet_gas_metrics_sync():
    if not GAS_BASE_NETWORK:
        return []

    gas_price_wei = hex_to_int(call_json_rpc(GAS_BASE_NETWORK, "eth_gasPrice", []))

    points = [
        create_point("arkiv_mainnet_gas_price", gas_price_wei),
    ]
    points.extend(build_simulated_mainnet_spending_points())

    return points


async def collect_l1_sender_points():
    return await asyncio.to_thread(collect_l1_sender_points_sync)


async def run_infinite_loop():
    loop_count = 0
    print(f"Starting loop. Pushing selected metrics to InfluxDB at {INFLUXDB_URL}...")

    # Background task for folder size
    asyncio.create_task(
        get_path_size_async_loop("sequencer-data/geth", "arkiv_geth_db_size", "sequencer")
    )
    asyncio.create_task(
        get_path_size_async_loop("validator-data/geth", "arkiv_geth_db_size", "validator")
    )
    asyncio.create_task(
        get_path_size_async_loop(
            "sequencer-data/golem-base.db", "arkiv_pebble_db_size", "sequencer"
        )
    )
    asyncio.create_task(
        get_path_size_async_loop(
            "validator-data/golem-base.db", "arkiv_pebble_db_size", "validator"
        )
    )
    asyncio.create_task(get_path_size_async_loop("da-data", "arkiv_da_data_size"))
    asyncio.create_task(get_free_space_async_loop())

    # Initialize the Async InfluxDB Client
    async with InfluxDBClientAsync(
        url=INFLUXDB_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG,
    ) as client:
        write_api = client.write_api()

        while True:
            try:
                loop_count += 1
                metrics_state["batch_job_iteration_number"] = loop_count

                # Update SQLite file sizes directly in the state
                metrics_state["arkiv_sqlite_db_size_bytes"]["sequencer"] = get_file_size(
                    "sequencer-data/golem-base.db"
                )
                metrics_state["arkiv_sqlite_wal_size_bytes"]["sequencer"] = get_file_size(
                    "sequencer-data/golem-base.db-wal"
                )

                metrics_state["arkiv_sqlite_db_size_bytes"]["validator"] = get_file_size(
                    "validator-data/golem-base.db"
                )
                metrics_state["arkiv_sqlite_wal_size_bytes"]["validator"] = get_file_size(
                    "validator-data/golem-base.db-wal"
                )

                # --- Build InfluxDB Points ---
                points = []
                l1_points = []

                # Translate our state dictionary into InfluxDB Points
                for key, val in metrics_state.items():
                    if isinstance(val, dict):
                        for node_type, size in val.items():
                            points.append(create_point(key, size, {"node": node_type}))
                    else:
                        points.append(create_point(key, val))

                try:
                    points.extend(await collect_celestia_balance_points())
                except Exception as exc:
                    print(f"Failed to fetch Celestia account balance: {exc}")

                try:
                    points.extend(
                        await asyncio.to_thread(collect_mainnet_gas_metrics_sync)
                    )
                except Exception as exc:
                    print(f"Failed to collect mainnet gas metrics: {exc}")

                try:
                    points.extend(
                        await asyncio.to_thread(collect_celestia_da_gas_metrics_sync)
                    )
                except Exception as exc:
                    print(f"Failed to collect Celestia DA gas metrics: {exc}")

                try:
                    l1_points = await collect_l1_sender_points()
                    points.extend(l1_points)
                    log_prepared_l1_points(loop_count, l1_points)
                except Exception as exc:
                    print(f"Failed to collect L1 sender metrics: {exc}")

                points.extend(await collect_scraped_metrics_points())

                # --- Push to InfluxDB ---
                if l1_points:
                    print(
                        f"[l1-tracker] iteration {loop_count}: writing {len(l1_points)} "
                        f"L1 point(s) to bucket={INFLUX_BUCKET} url={INFLUXDB_URL}"
                    )
                await write_api.write(bucket=INFLUX_BUCKET, record=points)
                if l1_points:
                    print(
                        f"[l1-tracker] iteration {loop_count}: write completed for "
                        f"{len(l1_points)} L1 point(s)"
                    )

                print(f"Pushed iteration: {loop_count}")
                await asyncio.sleep(PUSH_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(run_infinite_loop())
