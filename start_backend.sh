#!/bin/bash
source .venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
nohup python -m uvicorn agentic_fleet.api.app:app --reload --port 8000 > backend.log 2>&1 &
echo "Backend started with PID $!" > backend_pid.txt
