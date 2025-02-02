#!/bin/bash
set -e

# Install package in development mode
pip install -e .

# Run the command
exec "$@"