FROM python:3.14-trixie

ARG ARKIV_RETH_TAG=v0.1.0-pure-0

RUN set -eux; \
    ARKIV_RETH_XZ_URL="https://github.com/Arkiv-Network/arkiv-op-reth/releases/download/${ARKIV_RETH_TAG}/arkiv-op-reth-${ARKIV_RETH_TAG}-linux-amd64.tar.xz"; \
    ARKIV_RETH_TGZ_URL="https://github.com/Arkiv-Network/arkiv-op-reth/releases/download/${ARKIV_RETH_TAG}/arkiv-op-reth-${ARKIV_RETH_TAG}-integration-tests.tar.gz"; \
    TMP_XZ="arkiv-reth.tar.xz"; \
    TMP_TGZ="arkiv-reth.tar.gz"; \
    if curl -fSL -o "$TMP_XZ" "$ARKIV_RETH_XZ_URL"; then \
        tar -xJf "$TMP_XZ"; \
    else \
        echo ".tar.xz not available, trying integration-tests tar.gz"; \
        curl -fSL -o "$TMP_TGZ" "$ARKIV_RETH_TGZ_URL"; \
        tar -xzf "$TMP_TGZ"; \
        rm -f "$TMP_TGZ"; \
    fi; \
    rm -f "$TMP_XZ"; \
    mv arkiv-node arkiv-cli /usr/local/bin/

WORKDIR /app

# The execution-layer entrypoint (run-el.sh) is bind-mounted by docker-compose,
# so the image only needs the arkiv-node / arkiv-cli binaries.
EXPOSE 8545 8546 8551 6160
