# Tier 1: Common web/HTTP packages
# Extends: tier0
# Adds: requests, httpx, aiohttp, pyyaml, beautifulsoup4, lxml
# Size: ~200MB

ARG REGISTRY=block-sandbox
FROM ${REGISTRY}-tier0:latest

USER root

RUN pip install --no-cache-dir \
    requests \
    httpx \
    aiohttp \
    pyyaml \
    beautifulsoup4 \
    lxml \
    python-dotenv

USER sandbox
