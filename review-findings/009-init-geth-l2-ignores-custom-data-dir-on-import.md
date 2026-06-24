# init_geth-l2.sh imports the signer into the wrong data directory

**Severity:** Medium

## Affected files

- `init_geth-l2.sh:6`
- `start_geth-l2.sh:6`

## Problem

`init_geth-l2.sh` supports `ARKIV_SQLITE_DATA_DIRECTORY` through `DATA_DIR`, and it uses that value for chain initialization, `genesis.json`, and `password.txt`. The account import command then hardcodes `--datadir data` instead of using `"$DATA_DIR"`.

`start_geth-l2.sh` also reads `ARKIV_SQLITE_DATA_DIRECTORY` and starts geth from `"$DATA_DIR"`, so a custom data directory will not contain the imported signer account.

## Impact

Deployments that set `ARKIV_SQLITE_DATA_DIRECTORY` initialize one data directory and import the signer into another. Startup then fails to unlock the signer from the configured data directory, or starts with a data directory that has no imported account.

## Evidence

`init_geth-l2.sh:6-13` sets and uses `DATA_DIR`:

```bash
DATA_DIR="${ARKIV_SQLITE_DATA_DIRECTORY:-data}"
./geth-l2 --datadir "$DATA_DIR" init ./genesis.json
echo "mysecretpassword" > ./"${DATA_DIR}"/password.txt
```

`init_geth-l2.sh:17` then imports into literal `data`:

```bash
./geth-l2 account import --datadir data --password ./"${DATA_DIR}"/password.txt signer.key
```

`start_geth-l2.sh:6-7` starts from the configured `DATA_DIR`.

## Suggested fix

Change the import command to `--datadir "$DATA_DIR"` and quote the value consistently. Add a simple shell test or documented smoke command that initializes and starts with a non-default `ARKIV_SQLITE_DATA_DIRECTORY`.
