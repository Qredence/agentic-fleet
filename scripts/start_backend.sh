#!/bin/bash
set -euo pipefail

nohup uv run uvicorn agentic_fleet.main:app --reload --port 8000 --log-level info \
	> backend.log 2>&1 &
echo "Backend started with PID $!" > backend_pid.txt
