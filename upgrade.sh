#!/bin/bash
# Full path: axon_bbs/upgrade.sh
# Axon BBS Upgrade Script

echo "--- Starting Axon BBS Upgrade ---"

# Activate the virtual environment
source venv/bin/activate

# Step 1: Pull the latest code
echo "[1/4] Pulling latest code from Git..."
git pull
if [ $? -ne 0 ]; then
    echo "ERROR: git pull failed. Aborting upgrade."
    exit 1
fi

# Step 2: Install/update dependencies
echo "[2/4] Installing Python dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: pip install failed. Aborting upgrade."
    exit 1
fi

# Step 3: Apply database migrations
echo "[3/4] Applying database migrations..."
python manage.py migrate
if [ $? -ne 0 ]; then
    echo "ERROR: Django migrations failed. Aborting upgrade."
    exit 1
fi

# Step 4: Restart the server (example using systemd)
echo "[4/4] Restarting the Axon BBS server..."
# Replace with the actual command you use to run the server
# For example: sudo systemctl restart axon-bbs.service
# Or if you use gunicorn directly: pkill gunicorn; gunicorn ...
echo "Please restart the server process manually if not using an automated service."

echo "--- Upgrade Complete ---"
