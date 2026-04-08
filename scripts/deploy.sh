#!/bin/bash

# GenStep AI Deployment Script
# Zips the project, scps to Raspberry Pi, and setups environment.

# Configuration
PROJECT_NAME="genstep"
DEFAULT_HOST="genstep"
DEFAULT_DEST_PATH="~/genstep"
ZIP_FILE="genstep.zip"

# Use first argument if provided, otherwise fallback to default host
SSH_HOST=${1:-$DEFAULT_HOST}

echo "--- Deploying $PROJECT_NAME to SSH host: $SSH_HOST ---"

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
echo "[2/4] Transferring $ZIP_FILE to $SSH_HOST..."
scp $ZIP_FILE $SSH_HOST:~/

if [ $? -ne 0 ]; then
    echo "Error: scp failed. Make sure SSH host '$SSH_HOST' is reachable."
    rm $ZIP_FILE
    exit 1
fi

# 4. Remote setup (Unzip, install dependencies)
echo "[3/4] Unpacking and installing dependencies on Pi..."
ssh $SSH_HOST << EOF
    mkdir -p $DEFAULT_DEST_PATH
    unzip -o ~/genstep.zip -d $DEFAULT_DEST_PATH
    rm ~/genstep.zip
    cd $DEFAULT_DEST_PATH
    
    # Create venv if not exists
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment on Pi..."
        python3 -m venv venv
    fi

    # Install dependencies into venv
    if [ -f requirements.txt ]; then
        echo "Installing requirements into venv..."
        ./venv/bin/pip install -r requirements.txt
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
echo "You can now run the app on the Pi: ssh $SSH_HOST '$DEFAULT_DEST_PATH/venv/bin/python $DEFAULT_DEST_PATH/src/main.py'"
