FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash sandbox && \
    mkdir -p /output /tmp && \
    chown sandbox:sandbox /output /tmp && \
    chmod 1777 /output /tmp

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

RUN pip install --no-cache-dir \
    numpy \
    pandas \
    requests \
    httpx \
    pyyaml \
    beautifulsoup4 \
    lxml

WORKDIR /tmp

USER sandbox

CMD ["sleep", "infinity"]
