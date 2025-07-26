FROM ubuntu:22.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3 dnsutils && \
    rm -rf /var/lib/apt/lists/*

# Copy defense script
COPY defense.py /app/defense.py

# Make defense script executable
RUN chmod +x /app/defense.py

# Set working directory
WORKDIR /app

# Run defense proxy on port 53
CMD ["python3", "defense.py"]
