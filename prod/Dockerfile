FROM python:3.14-trixie

ARG ARKIV_RETH_TAG=v0.1.0-pure-0

RUN curl -fSL "https://github.com/Arkiv-Network/arkiv-op-reth/releases/download/${ARKIV_RETH_TAG}/arkiv-op-reth-${ARKIV_RETH_TAG}-linux-amd64.tar.xz" | tar -xJ \
    && mv arkiv-node arkiv-cli /usr/local/bin/

WORKDIR /app
COPY run-sequencer.sh .
COPY generate-genesis-entrypoint.sh .
COPY generate-pure-reth-genesis.py .
COPY test-accounts.txt .
RUN chmod +x run-sequencer.sh
RUN chmod +x generate-genesis-entrypoint.sh

EXPOSE 8545 8546 6160
ENTRYPOINT ["/bin/bash", "run-sequencer.sh"]
