FROM ubuntu:22.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3 && \
    rm -rf /var/lib/apt/lists/*

# Copy the DNS proxy script
COPY dns_proxy_delay.py /app/dns_proxy_delay.py
RUN chmod +x /app/dns_proxy_delay.py

# Start the DNS proxy with delay (unbuffered output)
ENTRYPOINT ["python3", "-u", "/app/dns_proxy_delay.py"]
