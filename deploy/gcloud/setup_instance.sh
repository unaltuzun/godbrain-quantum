#!/bin/bash
# Run this ON the Google Cloud instance

set -e

echo "🔧 Setting up VOLTRAN Evolution Server..."

# Update system
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv redis-server supervisor git

# Start Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Create app directory
sudo mkdir -p /opt/godbrain
sudo chown $USER:$USER /opt/godbrain
cd /opt/godbrain

# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install redis numpy

# Create genetics folder
mkdir -p genetics logs

echo "✅ Base setup complete!"
echo "Now copy the lab files to /opt/godbrain/genetics/"
echo "Then run: ./start_labs.sh"
