#!/bin/bash
set -e

# Create venv on volume if not exists
if [ ! -d "/models/venv" ]; then
    echo "Creating virtual environment on volume..."
    python -m venv /models/venv
fi

# Activate venv
source /models/venv/bin/activate

# Install/update requirements
echo "Installing requirements..."
pip install -q -r /app/requirements.txt

# Run the app
exec uvicorn app:app --host 0.0.0.0 --port 8080
