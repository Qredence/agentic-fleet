"""Test configuration and fixtures."""
import os
from typing import Generator

import pytest
from dotenv import load_dotenv


@pytest.fixture(autouse=True)
def setup_test_env() -> Generator:
    """Set up test environment variables."""
    # Store current environment
    old_environ = dict(os.environ)
    
    # Load test environment
    load_dotenv(".env.test", override=True)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(old_environ)
