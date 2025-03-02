"""
Pytest configuration file.
"""

import os
import sys
from pathlib import Path

import pytest

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables
os.environ["TESTING"] = "True"
os.environ["API_KEY"] = "test_api_key"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up the test environment.
    """
    # Save original environment variables
    original_env = os.environ.copy()

    # Set test environment variables
    os.environ["TESTING"] = "True"
    os.environ["API_KEY"] = "test_api_key"

    yield

    # Restore original environment variables
    for key, value in original_env.items():
        os.environ[key] = value

    # Remove any added environment variables
    for key in os.environ.keys() - original_env.keys():
        del os.environ[key]
