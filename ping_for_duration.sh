#!/bin/bash

# This script will ping a target host for a specified duration
# Usage: ./ping_for_duration.sh <target> <duration>

# Check for required arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <target IP> <duration>"
    exit 1
fi

# Assign arguments to variables
target=$1
duration=$2

# Validate target IP format (IPv4)
if [[ ! $target =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Invalid target IP address"
    exit 1
fi

# Validate duration format (positive integer)
if ! [[ $duration =~ ^[0-9]+$ ]]; then
    echo "Invalid duration"
    exit 1
fi

# Start time for tracking elapsed time
start_time=$(date +%s)

# Loop until the elapsed time exceeds the specified duration
#while [ $(($(date +%s) - $start_time)) -lt $duration ]; do
while true; do
    # Check if elapsed time exceeds the specified duration
    elapsed_time=$(($(date +%s) - $start_time))
    if [ $elapsed_time -ge $duration ]; then
        break
    fi
    ping -v -O -w $(($duration - $elapsed_time)) $target
    #ping -c 1 $target
    if [ $? -eq 0 ]; then
        echo "Ping successful"
    else
        echo "Ping failed to $target at $(date). Retrying..."
    fi
done
