#!/bin/bash

# Only run once
if [ -f /var/log/startup_already_done ]; then
    echo "Startup already ran. Skipping."
    exit 0
fi

echo "Starting VM2 startup script..."

# Update and install Python
apt-get update -y
apt-get install -y python3-pip

touch /var/log/startup_already_done
echo "VM2 client startup complete."
