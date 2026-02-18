FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    pkg-config \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pre-install commonly needed Python packages
RUN pip install --no-cache-dir \
    pytest \
    pytest-xdist \
    coverage \
    hypothesis \
    tox \
    setuptools \
    wheel \
    pip --upgrade

WORKDIR /testbed

CMD ["/bin/bash"]
