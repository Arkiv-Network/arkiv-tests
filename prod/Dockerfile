FROM python:3.14-trixie

ARG ARKIV_RETH_TAG=v0.1.0-pure-0

RUN curl -fSL "https://github.com/Arkiv-Network/arkiv-op-reth/releases/download/${ARKIV_RETH_TAG}/arkiv-op-reth-${ARKIV_RETH_TAG}-linux-amd64.tar.xz" | tar -xJ \
    && mv arkiv-node arkiv-cli /usr/local/bin/

WORKDIR /app

# The execution-layer entrypoint (run-el.sh) is bind-mounted by docker-compose,
# so the image only needs the arkiv-node / arkiv-cli binaries.
EXPOSE 8545 8546 8551 6160
