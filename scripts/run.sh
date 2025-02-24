#!/bin/zsh

# Get the project root directory
PROJECT_ROOT=$(dirname $(dirname $0))

# Set environment variables
export PYTHONPATH=$PROJECT_ROOT/src

# Activate virtual environment
source $PROJECT_ROOT/.venv/bin/activate

# Run the application using CLI command
agenticfleet start no-oauth --host localhost --port 8002
