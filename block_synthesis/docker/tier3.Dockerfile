# Tier 3: Scientific/ML packages
# Extends: tier2
# Adds: scipy, scikit-learn, opencv, matplotlib
# Size: ~800MB

ARG REGISTRY=block-sandbox
FROM ${REGISTRY}-tier2:latest

USER root

# Install additional system dependencies for opencv/scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    scipy \
    scikit-learn \
    opencv-python-headless \
    matplotlib \
    seaborn \
    statsmodels

USER sandbox
