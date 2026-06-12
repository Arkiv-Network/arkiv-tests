import logging
import sys
import threading
import time
from pathlib import Path

file_dir = Path(__file__).resolve().parent
project_root = file_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import web3
from web3 import Account, Web3

import stress.tools.config as config
from stress.tools.utils import build_account_path

logging.basicConfig(level=logging.INFO)
Account.enable_unaudited_hdwallet_features()

TOPUP_AMOUNT_ETH = 10
MIN_BALANCE_ETH = 1

w3 = Web3(web3.HTTPProvider(endpoint_uri=config.host))

if not w3.is_connected():
    logging.error(f"Not connected to RPC at {config.host}")
    raise SystemExit(1)

funder = Account.from_key(config.founder_key)
logging.info(f"Connected to {config.host}, funder: {funder.address}")

# Collect accounts that need a top-up
accounts_to_topup = []
for i in range(config.users):
    account_path = build_account_path(i)
    account = Account.from_mnemonic(config.mnemonic, account_path=account_path)
    balance = Web3.from_wei(w3.eth.get_balance(account.address), "ether")
    logging.info(f"User {i}: {account.address}, balance: {balance} ETH")
    if balance < MIN_BALANCE_ETH:
        accounts_to_topup.append((i, account))
    else:
        logging.info(f"User {i}: balance sufficient, skipping")

if not accounts_to_topup:
    logging.info("All accounts have sufficient balance, nothing to do")
    raise SystemExit(0)

# Fetch nonce once and send all transactions without waiting for receipts
nonce = w3.eth.get_transaction_count(funder.address)
gas_price = w3.eth.gas_price
chain_id = w3.eth.chain_id

# Maps tx_hash -> user index so the receipt listener can log results
pending: dict[str, int] = {}

TXPOOL_RETRY_DELAY = 2
TXPOOL_FULL_CODE = -32003

for i, account in accounts_to_topup:
    signed = funder.sign_transaction({
        "from": funder.address,
        "to": account.address,
        "value": Web3.to_wei(TOPUP_AMOUNT_ETH, "ether"),
        "gas": 21000,
        "gasPrice": gas_price,
        "nonce": nonce,
        "chainId": chain_id,
    })
    while True:
        try:
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            break
        except web3.exceptions.Web3RPCError as e:
            if e.rpc_response and e.rpc_response.get("error", {}).get("code") == TXPOOL_FULL_CODE:
                logging.warning(f"User {i}: txpool full, retrying in {TXPOOL_RETRY_DELAY}s...")
                time.sleep(TXPOOL_RETRY_DELAY)
            else:
                raise
    tx_hex = tx_hash.hex()
    pending[tx_hex] = i
    logging.info(f"User {i}: sent top-up tx {tx_hex} (nonce={nonce})")
    nonce += 1

# Watch for receipts in a background thread; break on any failure because a
# rejected nonce N leaves all subsequent nonces as future nonces that will
# never be mined.
failed = threading.Event()

def watch_receipts():
    for tx_hex, user_index in list(pending.items()):
        if failed.is_set():
            logging.error(f"User {user_index}: skipping receipt check — earlier tx failed")
            continue
        try:
            receipt = w3.eth.wait_for_transaction_receipt(
                bytes.fromhex(tx_hex.removeprefix("0x")),
                timeout=config.timeout_tx_to_be_mined,
            )
            if receipt.status == 1:
                new_balance = Web3.from_wei(
                    w3.eth.get_balance(
                        Account.from_mnemonic(
                            config.mnemonic,
                            account_path=build_account_path(user_index),
                        ).address
                    ),
                    "ether",
                )
                logging.info(
                    f"User {user_index}: top-up confirmed, new balance: {new_balance} ETH"
                )
            else:
                logging.error(
                    f"User {user_index}: tx {tx_hex} was REVERTED (status=0) — stopping"
                )
                failed.set()
        except Exception as e:
            logging.error(
                f"User {user_index}: error waiting for tx {tx_hex}: {e} — stopping"
            )
            failed.set()

watcher = threading.Thread(target=watch_receipts, daemon=False)
watcher.start()
watcher.join()

if failed.is_set():
    logging.error("Top-up aborted: one or more transactions failed")
    raise SystemExit(1)

logging.info("All top-ups confirmed successfully")
