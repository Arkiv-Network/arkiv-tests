FROM python:3.14-trixie

RUN curl -sL https://github.com/foundry-rs/foundry/releases/download/v1.5.1/foundry_v1.5.1_linux_amd64.tar.gz | tar -xz \
    && mv forge cast anvil chisel /usr/local/bin/

RUN curl -sL https://github.com/salad-x-golem/yagna-arkiv-market-matcher/releases/download/v0.0.0/optimism-binaries-2026-01-22.tar.xz | tar -xJ \
    && mv op-deployer op-geth op-node /usr/local/bin/

WORKDIR /app
COPY start.sh .
COPY generate-intent.py .
COPY anvil-chain.json .
RUN chmod +x start.sh
ENTRYPOINT ["/bin/bash", "start.sh"]