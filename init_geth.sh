#!/usr/bin/env bash

set -x

./geth --datadir "${GETH_SQLITE_DATA_DIRECTORY:-data}" init ./genesis.json

