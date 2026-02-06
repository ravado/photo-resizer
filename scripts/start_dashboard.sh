#!/bin/bash

# Ensure we are in the project root
cd "$(dirname "$0")/.."

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Please create one first."
    exit 1
fi

# Run Dashboard (Port 80 requires root/sudo)
exec uvicorn dashboard.main:app --host 0.0.0.0 --port 80
