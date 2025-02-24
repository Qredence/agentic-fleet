#!/bin/bash
set -ex

echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

# Install package in development mode
echo "Installing package in development mode..."
pip install -e .

echo "Command to execute: $@"
# Run the command
exec "$@"