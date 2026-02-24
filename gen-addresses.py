import argparse
import os

import requests
from eth_account import Account

Account.enable_unaudited_hdwallet_features()

DEFAULT_COUNT = 10


def build_account_path(user_index: int) -> str:
    instance_index = 0
    return f"m/44'/60'/{instance_index}'/0/{user_index}"


def derive_addresses(mnemonic: str, count: int) -> list[str]:
    addresses = []
    for i in range(count):
        account_path = build_account_path(i)
        account = Account.from_mnemonic(mnemonic, account_path=account_path)
        addresses.append(account.address)
    return addresses

mnemonic="parent picture garment parrot churn record stadium pill rocket craft fish fiscal clip virus view diary replace wealth extra kitten door enforce piece nut"
addres = derive_addresses(mnemonic, 1000)
with open("test-accounts.txt", "w") as f:
    for addr in addres:
        f.write(addr + "\n")

