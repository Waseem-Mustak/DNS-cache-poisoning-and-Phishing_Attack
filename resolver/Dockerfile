FROM ubuntu:22.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y bind9 dnsutils && \
    rm -rf /var/lib/apt/lists/*

# Copy resolver config
COPY named.conf.options /etc/bind/named.conf.options

# Run named in foreground
CMD ["named", "-g", "-c", "/etc/bind/named.conf.options"]
