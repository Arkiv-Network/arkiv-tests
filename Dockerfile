FROM python:3.14-trixie

RUN apt update && apt install jq -y

# Download necessary binaries
RUN curl -sL https://github.com/foundry-rs/foundry/releases/download/v1.5.1/foundry_v1.5.1_linux_amd64.tar.gz | tar -xz \
    && mv forge cast anvil chisel /usr/local/bin/ \
    && curl -sL https://github.com/salad-x-golem/yagna-arkiv-market-matcher/releases/download/v0.0.0/op-node-v1.16.2-1b8c5410.tar.xz | tar -xJ \
    && mv op-node /usr/local/bin/ \
    && curl -sL https://github.com/salad-x-golem/arkiv-op-geth/releases/download/v1.101605.0-metrics.0/arkiv-op-geth-v1.101605.0-metrics.0-linux-amd64.tar.xz | tar -xJ \
    && mv op-geth /usr/local/bin/ \
    && curl -sL https://github.com/salad-x-golem/yagna-arkiv-market-matcher/releases/download/v0.0.0/arkiv-op-deployer-0.4.4-1.tar.xz | tar -xJ \
    && mv op-deployer /usr/local/bin/

WORKDIR /app
COPY start_arkiv.sh .
COPY generate-intent-arkiv.py .
COPY docker-accounts.txt test-accounts.txt
COPY patch-genesis.py .
COPY anvil-chain.json .
RUN chmod +x start_arkiv.sh
ENTRYPOINT ["/bin/bash", "start_arkiv.sh"]