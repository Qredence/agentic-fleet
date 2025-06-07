import os
import pytest
from unittest.mock import patch
from agentic_fleet.config import config_manager

@pytest.fixture(scope="function", autouse=True)
def manage_environment_variables():
    """Ensures environment variables are cleaned up after each test."""
    original_env = os.environ.copy()
    # It's important that config_manager is re-evaluated if its internal state
    # depends on initial environment variable load.
    # For this test, we are mostly mocking os.getenv.
    yield
    os.environ.clear()
    os.environ.update(original_env)
    # Reload config_manager or relevant parts if it caches env vars internally at load time
    # For now, assume validate_environment directly uses os.getenv or is passed env vars.
    # config_manager.load_all() # If it needs to be forced to re-read.

def test_validate_environment_success(monkeypatch):
    """Test validate_environment succeeds when all required variables are set."""
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "test_endpoint")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "test_version")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "test_deployment")

    # In config/__init__.py, validate_environment() has a fallback to an internal list.
    # It also has a path `if 'validate_env_vars' in globals(): return validate_env_vars()`
    # We are testing the fallback path primarily, or assuming validate_env_vars does similar.

    error_message = config_manager.validate_environment()
    assert error_message is None

@pytest.mark.parametrize("missing_var", [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_DEPLOYMENT",
])
def test_validate_environment_missing_one_variable(missing_var, monkeypatch):
    """Test validate_environment fails if a required Azure variable is missing."""
    env_vars = {
        "AZURE_OPENAI_API_KEY": "test_key",
        "AZURE_OPENAI_ENDPOINT": "test_endpoint",
        "AZURE_OPENAI_API_VERSION": "test_version",
        "AZURE_OPENAI_DEPLOYMENT": "test_deployment",
    }
    # Remove the variable to be tested as missing
    if missing_var in env_vars:
        monkeypatch.delenv(missing_var, raising=False)
        # Set the rest
        for k,v in env_vars.items():
            if k != missing_var:
                monkeypatch.setenv(k,v)
    else: # Should not happen with parametrize
        pytest.fail(f"Unknown missing_var: {missing_var}")

    error_message = config_manager.validate_environment()
    assert error_message is not None
    assert missing_var in error_message
    assert "Missing required environment variables" in error_message

def test_validate_environment_missing_multiple_variables(monkeypatch):
    """Test validate_environment fails and lists multiple missing variables."""
    # None of the required Azure variables are set
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)

    error_message = config_manager.validate_environment()
    assert error_message is not None
    assert "Missing required environment variables" in error_message
    assert "AZURE_OPENAI_API_KEY" in error_message
    assert "AZURE_OPENAI_ENDPOINT" in error_message
    assert "AZURE_OPENAI_API_VERSION" in error_message
    assert "AZURE_OPENAI_DEPLOYMENT" in error_message

# Test the scenario where validate_env_vars from settings is used.
# This requires a bit more setup to ensure that path is taken in config_manager.validate_environment.
# For now, we assume the list of required vars is the same.
# If `agentic_fleet.config.settings.validate_env_vars` exists and is different,
# more complex mocking of the globals() check or that function itself would be needed.
# The current implementation of config_manager.validate_environment in the provided file content
# defaults to its own list if the settings.validate_env_vars is not found in globals(),
# which is typical unless that function is explicitly imported and made global within config/__init__.py's scope.
# The provided code for config/__init__.py for ConfigurationManager is:
# if 'validate_env_vars' in globals(): return validate_env_vars()
# else: required_vars = [...]
# So we are primarily testing the 'else' block.

# To test the `if 'validate_env_vars' in globals():` path:
# We would need to mock `globals()` for the `config_manager` module or patch `validate_env_vars`
# directly if it's imported into `agentic_fleet.config`.

# Example (conceptual) for testing the other path:
# @patch('agentic_fleet.config.settings.validate_env_vars')
# def test_validate_environment_uses_settings_validate_env_vars(mock_settings_validate, monkeypatch):
#     # This test assumes 'validate_env_vars' from 'agentic_fleet.config.settings'
#     # is successfully imported into the 'agentic_fleet.config' namespace and thus in globals()
#     # of config_manager when it runs.
#     # This is a structural assumption about how config/__init__.py is written.
#
#     # To truly force this path, we might need to patch 'agentic_fleet.config.validate_env_vars'
#     # if that's where it would be found by `globals()`.
#
#     # For now, the current tests cover the primary logic path shown in the provided config_manager code.
#     pass
