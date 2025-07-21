FROM python:3.10-slim

# Install dependencies
RUN pip install flask scapy

# Create a directory for logs
RUN mkdir /data

# Copy attacker scripts
COPY phishing_server.py attack.py /app/
WORKDIR /app

# Ensure executables
RUN chmod +x phishing_server.py attack.py

# Default command: launch sniffer and phishing server in parallel
CMD ["bash", "-c", "python3 phishing_server.py"]
