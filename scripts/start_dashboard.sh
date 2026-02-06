#!/bin/bash

# Resolve absolute path of project root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Log startup info
echo "Starting Dashboard from $PROJECT_ROOT"
echo "Current user: $(whoami)"

# Find Python interpreter
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif [ -f "$PROJECT_ROOT/venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python"
else
    echo "ERROR: Python interpreter not found in .venv or venv."
    echo "Contents of $PROJECT_ROOT/:"
    ls -la "$PROJECT_ROOT/"
    exit 127
fi

echo "Using Python: $PYTHON"

# Run Dashboard (Port 80 requires root, which this script should be running as)
exec "$PYTHON" -m uvicorn dashboard.main:app --host 0.0.0.0 --port 80
