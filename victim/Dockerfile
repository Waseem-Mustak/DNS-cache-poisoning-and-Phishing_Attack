FROM ubuntu:20.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    dnsutils \
    iputils-ping \
    net-tools \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

CMD ["/bin/bash"]
