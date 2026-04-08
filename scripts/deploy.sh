#!/bin/bash

# GenStep AI Deployment Script
# Zips the project, scps to Raspberry Pi, and setups environment.

# Configuration
PROJECT_NAME="genstep"
DEFAULT_USER="pi"
DEFAULT_DEST_PATH="~/genstep"
ZIP_FILE="genstep.zip"

# Usage check
if [ "$1" == "" ]; then
    echo "Usage: ./scripts/deploy.sh [PI_IP] [PI_USER]"
    echo "Example: ./scripts/deploy.sh 192.168.1.100 pi"
    exit 1
fi

PI_IP=$1
PI_USER=${2:-$DEFAULT_USER}

echo "--- Deploying $PROJECT_NAME to $PI_USER@$PI_IP ---"

# 1. Clean up old artifacts locally
[ -f $ZIP_FILE ] && rm $ZIP_FILE

# 2. Creating ZIP archive (excluding git, venv, and local artifacts)
echo "[1/4] Packing project (excluding git, venv, pycache)..."
zip -r $ZIP_FILE . -x "*.git*" "venv/*" ".venv/*" "**/__pycache__/*" ".DS_Store" "data/calibration.json" "*.zip" "build/*" "dist/*" > /dev/null

if [ $? -ne 0 ]; then
    echo "Error: Failed to create zip file."
    exit 1
fi

# 3. Transfer to Pi
echo "[2/4] Transferring $ZIP_FILE to $PI_USER@$PI_IP..."
scp $ZIP_FILE $PI_USER@$PI_IP:~/

if [ $? -ne 0 ]; then
    echo "Error: scp failed. Make sure SSH is enabled and credentials are correct."
    rm $ZIP_FILE
    exit 1
fi

# 4. Remote setup (Unzip, install dependencies)
echo "[3/4] Unpacking and installing dependencies on Pi..."
ssh $PI_USER@$PI_IP << EOF
    mkdir -p $DEFAULT_DEST_PATH
    unzip -o ~/genstep.zip -d $DEFAULT_DEST_PATH
    rm ~/genstep.zip
    cd $DEFAULT_DEST_PATH
    # Install dependencies
    if [ -f requirements.txt ]; then
        pip3 install -r requirements.txt
    fi
    echo "Deployment successful."
EOF

if [ $? -ne 0 ]; then
    echo "Error: Remote commands failed."
    rm $ZIP_FILE
    exit 1
fi

# 5. Clean up local zip
echo "[4/4] Cleaning up local ZIP..."
rm $ZIP_FILE

echo "--- Deployment Complete! ---"
echo "You can now run the app on the Pi: ssh $PI_USER@$PI_IP 'python3 $DEFAULT_DEST_PATH/src/main.py'"
