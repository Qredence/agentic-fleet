#!/usr/bin/env python
"""
Test runner script for the Agentic Fleet project.

This script uses pytest to run all tests in the project.
You can run all tests or specify particular test files or directories.

Usage:
    python run_tests.py                  # Run all tests
    python run_tests.py test_app.py      # Run a specific test file
    python run_tests.py unit/            # Run tests in a specific directory
    python run_tests.py -v               # Run with verbose output
    python run_tests.py -xvs             # Run with verbose output, stop on first failure
"""

import sys
import pytest


def run_tests():
    """Run the tests with the provided arguments."""
    args = sys.argv[1:]
    if not args:
        print("Running all tests...")
    else:
        print(f"Running tests with args: {' '.join(args)}")
    
    # Default arguments to include the asyncio fixture and show colors
    default_args = ["-v", "--color=yes"]
    
    # Combine default args with any user-provided args
    test_args = default_args + args
    
    # Run pytest with the combined arguments
    exit_code = pytest.main(test_args)
    
    # Return the pytest exit code
    return exit_code


if __name__ == "__main__":
    sys.exit(run_tests()) 