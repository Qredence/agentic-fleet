#!/bin/zsh

# Activate virtual environment
source $(dirname $(dirname $0))/.venv/bin/activate

# Set Python path
export PYTHONPATH=$(dirname $(dirname $0))/src

# Run the Chainlit app
chainlit run $(dirname $(dirname $0))/src/agentic_fleet/app.py --host localhost --port 8000
