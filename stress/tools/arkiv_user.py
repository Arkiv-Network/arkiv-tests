import logging
import time
from typing import Any, Optional

import web3
from arkiv import Arkiv
from arkiv.account import NamedAccount
from eth_account import Account
from eth_account.signers.local import LocalAccount
from locust import events
from web3 import Web3

import stress.tools.config as config
from stress.tools.json_rpc_user import JsonRpcUser
from stress.tools.utils import build_account_path

Account.enable_unaudited_hdwallet_features()

DEFAULT_BLOCK_DURATION_SECONDS = 2


class ArkivUser(JsonRpcUser):
    abstract = True

    account: Optional[LocalAccount] = None
    w3: Optional[Arkiv] = None
    block_duration_seconds: int = DEFAULT_BLOCK_DURATION_SECONDS

    def _initialize_account_and_w3(self) -> Arkiv:
        if self.account is None or self.w3 is None:
            account_path = build_account_path(self.id)
            logging.info("Mnemonic: " + config.mnemonic)
            self.account = Account.from_mnemonic(config.mnemonic, account_path=account_path)
            self.w3 = Arkiv(
                web3.HTTPProvider(endpoint_uri=self.client.base_url, session=self.client),
                NamedAccount(name="LocalSigner", account=self.account),
            )
            if not self.w3.is_connected():
                raise RuntimeError(f"Not connected to Arkiv RPC at {self.client.base_url}")
            if config.chain_env == "local":
                self._topup_local_account()
            try:
                block_timing = self.w3.arkiv.get_block_timing()
                self.block_duration_seconds = int(
                    getattr(block_timing, "duration", DEFAULT_BLOCK_DURATION_SECONDS)
                )
            except Exception:
                self.block_duration_seconds = DEFAULT_BLOCK_DURATION_SECONDS
        return self.w3

    def _topup_local_account(self) -> None:
        if self.w3 is None or self.account is None:
            return
        try:
            funder = Account.from_key(config.founder_key)
            balance = Web3.from_wei(self.w3.eth.get_balance(self.account.address), "ether")
            logging.debug(f"Account {self.account.address} has balance {balance}")
            logging.debug(f"Try to send funds from founder account {funder.address}")
            if balance < 0.0001:
                signed = funder.sign_transaction({
                    "from": funder.address,
                    "to": self.account.address,
                    "value": Web3.to_wei(0.1, "ether"),
                    "gas": 21000,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": self.w3.eth.get_transaction_count(funder.address),
                    "chainId": self.w3.eth.chain_id,
                })
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                self.w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as err:
            logging.error("Error while trying to local topup", err)

    def _expires_in_seconds_from_blocks(self, ttl_blocks: int) -> int:
        return max(1, int(ttl_blocks) * int(self.block_duration_seconds))

    def _fire_locust_request(self, name: str, fn) -> Any:
        start = time.perf_counter()
        exc: Optional[BaseException] = None
        try:
            return fn()
        except BaseException as e:
            exc = e
            raise
        finally:
            events.request.fire(
                request_type="arkiv",
                name=name,
                response_time=(time.perf_counter() - start) * 1000,
                response_length=0,
                exception=exc,
                context={},
                response=None,
            )

    def _is_not_found(self, e: BaseException) -> bool:
        msg = str(e).lower()
        return (
            "not found" in msg
            or "404" in msg
            or "missing" in msg
            or "does not exist" in msg
        )
