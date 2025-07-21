#!/bin/bash

# Try to add network delay first
if tc qdisc add dev eth0 root netem delay 500ms 2>/dev/null; then
    echo "Successfully added 500ms network delay using tc"
else
    echo "Warning: Could not add network delay using tc - no artificial delay will be added"
fi

# Start BIND
echo "Starting BIND DNS proxy..."
exec named -g -c /etc/bind/named.conf.options
