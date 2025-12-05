#!/bin/bash
set -euo pipefail

# Kill process on port 8000 to avoid conflicts
echo "Killing any process on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Run backend with uv (no manual venv activation required)
echo "Starting backend on port 8000..."
uv run uvicorn agentic_fleet.app.main:app --reload --port 8000 --log-level info
