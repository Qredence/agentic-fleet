#!/bin/bash
# Kill process on port 8000
echo "Killing any process on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Activate venv
source .venv/bin/activate

# Set PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# Run uvicorn
echo "Starting backend on port 8000..."
python -m uvicorn agentic_fleet.api.app:app --reload --port 8000
