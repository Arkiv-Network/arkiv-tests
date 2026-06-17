import json
import os
import sys
import time


WEI_PER_ETH = 10**18
DEFAULT_CHAIN_ID = 42069
DEFAULT_GAS_LIMIT = 30_000_000
DEFAULT_BLOCK_TIME_SECONDS = 2
DEFAULT_PREFUND_ETH = 10_000
DEFAULT_SIGNER_ADDRESS = "0x1e8254Ecb29AC73De90F02066A35b27f75FD5654"
INITIAL_BASE_FEE_WEI = 10_000_000
ZERO_HASH = "0x" + "00" * 32


def parse_int_env(name, default):
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default

    try:
        return int(raw_value, 0)
    except ValueError:
        print(f"Invalid integer for {name}: {raw_value}", file=sys.stderr)
        sys.exit(1)


def normalize_address(address):
    clean_address = address.strip()
    if not clean_address:
        return ""
    if not clean_address.startswith("0x"):
        clean_address = f"0x{clean_address}"
    if len(clean_address) != 42:
        print(f"Invalid Ethereum address: {address}", file=sys.stderr)
        sys.exit(1)
    return clean_address


def load_prefund_addresses(path):
    addresses = []
    seen = set()

    with open(path, encoding="utf-8") as handle:
        for line in handle:
            address = normalize_address(line)
            if not address:
                continue

            key = address.lower()
            if key in seen:
                continue

            seen.add(key)
            addresses.append(address)

    return addresses


def build_clique_extra_data(signer_address):
    signer_hex = normalize_address(signer_address)[2:].lower()
    return "0x" + ("00" * 32) + signer_hex + ("00" * 65)


def build_genesis(
    *,
    chain_id,
    signer_address,
    block_time_seconds,
    gas_limit,
    prefund_eth,
    prefund_addresses,
):
    signer_address = normalize_address(signer_address)
    balance = hex(prefund_eth * WEI_PER_ETH)
    alloc = {
        normalize_address(address): {"balance": balance}
        for address in prefund_addresses
    }
    alloc[signer_address] = {"balance": balance}

    return {
        "config": {
            "chainId": chain_id,
            "homesteadBlock": 0,
            "daoForkBlock": 0,
            "daoForkSupport": True,
            "eip150Block": 0,
            "eip150Hash": ZERO_HASH,
            "eip155Block": 0,
            "eip158Block": 0,
            "byzantiumBlock": 0,
            "constantinopleBlock": 0,
            "petersburgBlock": 0,
            "istanbulBlock": 0,
            "berlinBlock": 0,
            "londonBlock": 0,
            "shanghaiTime": 0,
            "cancunTime": 0,
            "pragueTime": 0,
            "clique": {
                "period": block_time_seconds,
                "epoch": 30_000,
            },
        },
        "nonce": "0x0",
        "timestamp": hex(int(time.time())),
        "extraData": build_clique_extra_data(signer_address),
        "gasLimit": hex(gas_limit),
        "difficulty": "0x1",
        "mixHash": ZERO_HASH,
        "coinbase": signer_address,
        "alloc": alloc,
        "baseFeePerGas": hex(INITIAL_BASE_FEE_WEI),
    }


def main():
    chain_id = parse_int_env("PURE_RETH_CHAIN_ID", DEFAULT_CHAIN_ID)
    gas_limit = parse_int_env("PURE_RETH_GAS_LIMIT", DEFAULT_GAS_LIMIT)
    block_time_seconds = parse_int_env(
        "PURE_RETH_BLOCK_TIME_SECONDS", DEFAULT_BLOCK_TIME_SECONDS
    )
    prefund_eth = parse_int_env("PURE_RETH_PREFUND_ETH", DEFAULT_PREFUND_ETH)
    signer_address = os.getenv("PURE_RETH_SIGNER_ADDRESS", DEFAULT_SIGNER_ADDRESS)
    accounts_file = os.getenv("PURE_RETH_ACCOUNTS_FILE", "test-accounts.txt")
    output_path = os.getenv("PURE_RETH_GENESIS_PATH", "genesis.json")

    genesis = build_genesis(
        chain_id=chain_id,
        signer_address=signer_address,
        block_time_seconds=block_time_seconds,
        gas_limit=gas_limit,
        prefund_eth=prefund_eth,
        prefund_addresses=load_prefund_addresses(accounts_file),
    )

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(genesis, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(
        "Wrote pure reth Clique genesis to "
        f"{output_path} with chainId={chain_id}, signer={signer_address}, "
        f"blockTime={block_time_seconds}s, gasLimit={gas_limit}"
    )


if __name__ == "__main__":
    main()
