"""
Pytest configuration file.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables
os.environ["TESTING"] = "True"
os.environ["API_KEY"] = "test_api_key"


@pytest.fixture
def mock_user_session():
    """Fixture to provide a mutable mock user session dict."""
    return {}


@pytest.fixture
def mock_settings_components():
    """
    Fixture to provide MagicMock for UI component factories/settings.
    """
    # Mocking common chainlit settings UI components expected in tests
    settings_components = {
        "ChatSettings": MagicMock(name="ChatSettings"),
        "Select": MagicMock(name="Select"),
        "Slider": MagicMock(name="Slider"),
        "UserSettings": MagicMock(name="UserSettings"),
        "Textarea": MagicMock(name="Textarea"),
    }
    # Each can be further configured for specific tests.
    return settings_components


@pytest.fixture
def mock_chainlit_elements():
    """
    Fixture to provide a dictionary of MagicMock UI elements for Chainlit integration.
    """
    # Example: Mocking text and other UI elements used in tests
    return {
        "text": MagicMock(name="Text"),
        "button": MagicMock(name="Button"),
        "element": MagicMock(name="Element"),
        "Message": MagicMock(name="Message"),  # Add Message mock that was missing
        # Add more Chainlit UI elements as needed by tests.
    }


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
