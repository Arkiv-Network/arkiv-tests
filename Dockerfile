FROM python:3.14-trixie

RUN curl -sL https://github.com/foundry-rs/foundry/releases/download/v1.5.1/foundry_v1.5.1_linux_amd64.tar.gz | tar -xz \
    && mv forge cast anvil chisel /usr/local/bin/

RUN curl -sL https://github.com/salad-x-golem/yagna-arkiv-market-matcher/releases/download/v0.0.0/optimism-binaries-2026-01-22.tar.xz | tar -xJ
RUN curl -sL https://github.com/salad-x-golem/yagna-arkiv-market-matcher/releases/download/v0.0.0/arkiv-op-geth-1.101605.0-1.1.tar.xz | tar -xJ
RUN curl -sL https://github.com/salad-x-golem/yagna-arkiv-market-matcher/releases/download/v0.0.0/arkiv-op-deployer-0.4.4-1.tar.xz | tar -xJ

RUN mv op-deployer op-geth op-node /usr/local/bin/

WORKDIR /app
COPY start_arkiv.sh .
COPY generate-intent-arkiv.py .
COPY anvil-chain.json .
RUN chmod +x start_arkiv.sh
ENTRYPOINT ["/bin/bash", "start_arkiv.sh"]