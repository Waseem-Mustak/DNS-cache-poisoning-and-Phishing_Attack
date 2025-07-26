FROM ubuntu:22.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y bind9 && \
    rm -rf /var/lib/apt/lists/*

# Copy configuration files
COPY named.conf.local /etc/bind/named.conf.local
COPY db.bank.lab /etc/bind/db.bank.lab

# Run named in foreground with explicit config
CMD ["named", "-g", "-c", "/etc/bind/named.conf.local"]
