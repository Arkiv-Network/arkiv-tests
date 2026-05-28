import logging
import sys
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

for i in range(config.users):
    account_path = build_account_path(i)
    account = Account.from_mnemonic(config.mnemonic, account_path=account_path)
    balance = Web3.from_wei(w3.eth.get_balance(account.address), "ether")
    logging.info(f"User {i}: {account.address}, balance: {balance} ETH")

    if balance < MIN_BALANCE_ETH:
        signed = funder.sign_transaction({
            "from": funder.address,
            "to": account.address,
            "value": Web3.to_wei(TOPUP_AMOUNT_ETH, "ether"),
            "gas": 21000,
            "gasPrice": w3.eth.gas_price,
            "nonce": w3.eth.get_transaction_count(funder.address),
            "chainId": w3.eth.chain_id,
        })
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        new_balance = Web3.from_wei(w3.eth.get_balance(account.address), "ether")
        logging.info(f"User {i}: topped up, new balance: {new_balance} ETH")
    else:
        logging.info(f"User {i}: balance sufficient, skipping")
