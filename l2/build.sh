#!/bin/bash


set -x
forge install foundry-rs/forge-std
forge install OpenZeppelin/openzeppelin-contracts

forge build