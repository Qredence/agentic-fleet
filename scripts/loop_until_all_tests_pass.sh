#!/bin/bash

# This script runs pytest in the project until all tests pass.
# Requires the project's .venv environment and Makefile test target.
# Do NOT use 'set -e' here, as we want to continue looping on test failure.

DELAY=2  # Seconds to wait between retries (change as needed)

while true; do
    echo "-------------------------------------------"
    echo ">>> Running tests..."
    make test
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        echo ">>> All tests passed!"
        break
    else
        echo ">>> Tests failed. Will retry in $DELAY seconds..."
        sleep $DELAY
    fi
done
