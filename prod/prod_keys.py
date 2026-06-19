#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import secrets
import sys
import uuid
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt
from eth_account import Account
from eth_utils import to_checksum_address

try:
    from py_ecc.bls import G2ProofOfPossession as bls
    from py_ecc.optimized_bls12_381 import curve_order
except ImportError as exc:
    raise SystemExit(
        "Missing py_ecc. Install dependencies with `pip install py-ecc` "
        "or through this repo's Python environment."
    ) from exc


VALIDATOR_BALANCE_GWEI = 32_000_000_000
TEST_ACCOUNTS_MNEMONIC = "style insect tray body company scan annual rebuild rely crazy patient anger"


def clean_hex(value: str, expected_bytes: int, name: str) -> str:
    raw = value.strip()
    if raw.startswith("0x"):
        raw = raw[2:]
    if len(raw) != expected_bytes * 2:
        raise ValueError(f"{name} must be {expected_bytes} bytes")
    int(raw, 16)
    return raw.lower()


def operator_address_from_private_key(private_key: str) -> str:
    return Account.from_key("0x" + clean_hex(private_key, 32, "OPERATOR_PRIVATE_KEY")).address


def validator_pubkey_from_private_key(private_key: str) -> str:
    raw = clean_hex(private_key, 32, "VALIDATOR_PRIVATE_KEY")
    sk = int(raw, 16)
    if sk <= 0 or sk >= curve_order:
        raise ValueError("VALIDATOR_PRIVATE_KEY is outside the BLS12-381 scalar field")
    return "0x" + bls.SkToPk(sk).hex()


def generate_validator_private_key() -> str:
    return "0x" + (secrets.randbelow(curve_order - 1) + 1).to_bytes(32, "big").hex()


def withdrawal_credentials(operator_address: str) -> str:
    address = clean_hex(operator_address, 20, "OPERATOR_ADDRESS")
    return "0x01" + ("00" * 11) + address


def write_lighthouse_keystore(private_key: str, validator_address: str, out_dir: Path) -> None:
    secret = "0x" + clean_hex(private_key, 32, "VALIDATOR_PRIVATE_KEY")
    pubkey = clean_hex(validator_address, 48, "VALIDATOR_ADDRESS")
    password = secrets.token_hex(16)
    salt = secrets.token_bytes(32)
    iv = secrets.token_bytes(16)
    derived = scrypt(password.encode(), salt, key_len=32, N=262144, r=8, p=1)
    cipher = AES.new(derived[:16], AES.MODE_CTR, nonce=b"", initial_value=int.from_bytes(iv, "big"))
    ciphertext = cipher.encrypt(bytes.fromhex(secret[2:]))
    checksum = hashlib.sha256(derived[16:32] + ciphertext).hexdigest()

    keystore = {
        "crypto": {
            "kdf": {
                "function": "scrypt",
                "params": {
                    "dklen": 32,
                    "n": 262144,
                    "r": 8,
                    "p": 1,
                    "salt": salt.hex(),
                },
                "message": "",
            },
            "checksum": {
                "function": "sha256",
                "params": {},
                "message": checksum,
            },
            "cipher": {
                "function": "aes-128-ctr",
                "params": {"iv": iv.hex()},
                "message": ciphertext.hex(),
            },
        },
        "description": "",
        "pubkey": pubkey,
        "path": "",
        "uuid": str(uuid.uuid4()),
        "version": 4,
    }

    keys_dir = out_dir / "gen" / "keys" / ("0x" + pubkey)
    secrets_dir = out_dir / "gen" / "secrets"
    keys_dir.mkdir(parents=True, exist_ok=True)
    secrets_dir.mkdir(parents=True, exist_ok=True)
    (keys_dir / "voting-keystore.json").write_text(json.dumps(keystore, indent=2) + "\n", encoding="utf-8")
    (secrets_dir / ("0x" + pubkey)).write_text(password + "\n", encoding="utf-8")


def generate_env(path: Path) -> None:
    operator_private_key = "0x" + secrets.token_hex(32)
    validator_private_key = generate_validator_private_key()
    validator_address = validator_pubkey_from_private_key(validator_private_key)
    operator_address = operator_address_from_private_key(operator_private_key)
    lines = [
        "RPC_PORT=8545",
        "WS_PORT=8546",
        "METRICS_PORT=6160",
        "BEACON_HTTP_PORT=5052",
        "ARKIV_SDK_JS_REF=main",
        f'TEST_ACCOUNTS_MNEMONIC="{TEST_ACCOUNTS_MNEMONIC}"',
        f"OPERATOR_PRIVATE_KEY={operator_private_key}",
        f"OPERATOR_ADDRESS={operator_address}",
        f"VALIDATOR_PRIVATE_KEY={validator_private_key}",
        f"VALIDATOR_ADDRESS={validator_address}",
        "BLOCK_GAS_LIMIT=30000000",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)


def validate_env() -> tuple[str, str, str, str]:
    operator_private_key = os.environ["OPERATOR_PRIVATE_KEY"]
    operator_address = os.environ["OPERATOR_ADDRESS"]
    validator_private_key = os.environ["VALIDATOR_PRIVATE_KEY"]
    validator_address = os.environ["VALIDATOR_ADDRESS"]
    derived_operator = operator_address_from_private_key(operator_private_key)
    if derived_operator.lower() != operator_address.lower():
        raise ValueError(f"OPERATOR_ADDRESS does not match OPERATOR_PRIVATE_KEY: expected {derived_operator}")
    derived_validator = validator_pubkey_from_private_key(validator_private_key)
    if derived_validator.lower() != validator_address.lower():
        raise ValueError(f"VALIDATOR_ADDRESS does not match VALIDATOR_PRIVATE_KEY: expected {derived_validator}")
    return operator_private_key, to_checksum_address(operator_address), validator_private_key, validator_address


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    env_parser = subparsers.add_parser("env")
    env_parser.add_argument("--out", default=".env")
    genesis_parser = subparsers.add_parser("genesis-validator")
    genesis_parser.add_argument("--out", default="config/additional-validators.txt")
    keystore_parser = subparsers.add_parser("keystore")
    keystore_parser.add_argument("--out-dir", default="validators")
    args = parser.parse_args()

    if args.command == "env":
        generate_env(Path(args.out))
        return 0

    _, operator_address, validator_private_key, validator_address = validate_env()
    if args.command == "genesis-validator":
        line = f"{validator_address}:{withdrawal_credentials(operator_address)}:{VALIDATOR_BALANCE_GWEI}\n"
        Path(args.out).write_text(line, encoding="utf-8")
    elif args.command == "keystore":
        write_lighthouse_keystore(validator_private_key, validator_address, Path(args.out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
