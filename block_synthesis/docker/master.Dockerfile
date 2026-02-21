# Master Docker Image
# Contains ALL packages from every block in the codebase
# Use this when you need a single image that supports all blocks
# 
# Build: docker build -f master.Dockerfile -t block-sandbox-master:latest .
# Or:    python build_master.py

FROM python:3.11-slim

# Install system dependencies for all packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create sandbox user with limited privileges
RUN useradd -m -s /bin/bash sandbox && \
    mkdir -p /output /tmp /app && \
    chown sandbox:sandbox /output /tmp /app && \
    chmod 1777 /output /tmp

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# =============================================================================
# Install ALL packages from existing blocks (discovered by build_master.py)
# =============================================================================

# Core / Web
RUN pip install --no-cache-dir \
    httpx \
    requests \
    aiohttp \
    beautifulsoup4 \
    lxml

# Data Processing
RUN pip install --no-cache-dir \
    numpy \
    pandas \
    pillow \
    openpyxl \
    xlrd

# Scientific / ML (included for common use cases)
RUN pip install --no-cache-dir \
    scipy \
    scikit-learn \
    opencv-python-headless \
    matplotlib \
    seaborn \
    statsmodels

# AI / LLM
RUN pip install --no-cache-dir \
    anthropic \
    openai \
    google-generativeai

# External Services
RUN pip install --no-cache-dir \
    stripe \
    sendgrid \
    elevenlabs

# Config / Utilities
RUN pip install --no-cache-dir \
    pyyaml \
    python-dotenv \
    jsonschema \
    pydantic \
    docker

# Set working directory
WORKDIR /app

# Default to sandbox user
USER sandbox

# Keep container running for exec
CMD ["sleep", "infinity"]
