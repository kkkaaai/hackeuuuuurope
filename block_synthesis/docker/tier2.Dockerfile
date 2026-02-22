# Tier 2: Data processing packages
# Extends: tier1
# Adds: numpy, pandas, pillow, openpyxl, xlrd
# Size: ~400MB

ARG REGISTRY=block-sandbox
FROM ${REGISTRY}-tier1:latest

USER root

RUN pip install --no-cache-dir \
    numpy \
    pandas \
    pillow \
    openpyxl \
    xlrd \
    csvkit \
    jsonschema

USER sandbox
