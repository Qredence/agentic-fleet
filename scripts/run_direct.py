#!/usr/bin/env python3
"""Direct runner for AgenticFleet."""

import os
import sys

# Add src directory to path
src_dir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
)
sys.path.insert(0, src_dir)

# Set environment variables
os.environ["USE_OAUTH"] = "false"
os.environ["OAUTH_CLIENT_ID"] = ""
os.environ["OAUTH_CLIENT_SECRET"] = ""

# Import and run CLI
from agentic_fleet.cli import cli

if __name__ == "__main__":
    cli(["start", "no-oauth", "--host", "localhost", "--port", "8000"])
