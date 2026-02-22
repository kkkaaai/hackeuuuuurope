# Tier 0: Base Python environment
# Contains: Python 3.11, pip, setuptools, build tools, sandbox user
# Size: ~150MB

FROM python:3.11-slim

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create sandbox user with limited privileges
RUN useradd -m -s /bin/bash sandbox && \
    mkdir -p /output /tmp /app && \
    chown sandbox:sandbox /output /tmp /app && \
    chmod 1777 /output /tmp

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Set working directory
WORKDIR /app

# Default to sandbox user
USER sandbox

# Keep container running for exec
CMD ["sleep", "infinity"]
