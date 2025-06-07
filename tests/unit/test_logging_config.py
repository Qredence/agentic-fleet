import logging
import io
import pytest # Assuming pytest is available for caplog

from agentic_fleet.core.config.logging import setup_global_logging
from agentic_fleet.config import config_manager # To potentially mock or inspect config

# Ensure app_settings.yaml has predictable values for testing
# For this test, let's assume app_settings.yaml specifies:
# logging:
#   level: "DEBUG"  # Using DEBUG for testing to capture more levels
#   format: "%(levelname)s:%(name)s:%(message)s"

@pytest.fixture(autouse=True)
def ensure_config_manager_initialized():
    """
    Ensure the config_manager is loaded before each test in this module.
    This is important because setup_global_logging relies on it.
    """
    try:
        config_manager.load_all()
    except Exception as e:
        # In a real test suite, you might have a shared fixture or setup
        # to handle config loading and mocking app_settings.yaml.
        # For now, print a warning if it fails.
        print(f"Warning: config_manager.load_all() failed during test setup: {e}")
        # We can proceed, setup_global_logging has fallbacks.

def test_logging_is_configured_globally_and_captures_messages(caplog):
    """
    Tests that setup_global_logging configures logging and messages are captured.
    """
    # Call the global logging setup
    # This will use the actual app_settings.yaml or fallbacks if issues occur.
    setup_global_logging()

    # Check if the confirmation message from setup_global_logging itself was logged
    # This depends on the final implementation of setup_global_logging
    assert any("Global logging configured successfully" in message or \
               "LoggingConfig not fully available" in message or \
               "Error configuring logging from LoggingConfig" in message
               for message in caplog.messages)

    # Test logging a message
    test_logger = logging.getLogger("my_test_logger")
    test_message = "This is a test message at INFO level."
    test_logger.info(test_message)

    # Check if the message was captured by caplog
    assert test_message in caplog.text

    # Verify the log level (based on assumed app_settings.yaml or fallback)
    # The root logger's level should be set by basicConfig
    # If app_settings.yaml has DEBUG, root level should be DEBUG.
    # If setup_global_logging fell back, it would be INFO.

    # We can check the level of the root logger
    root_logger_level = logging.getLogger().getEffectiveLevel()

    # Retrieve the expected level from config to make the test adaptable
    expected_level_str = "INFO" # Default fallback in setup_global_logging
    log_config = config_manager.get_logging_settings()
    if log_config and log_config.level:
        try:
            # Attempt to use the configured level if valid
            expected_level_str = log_config.level.upper()
            # Ensure it's a valid level name before converting to number
            if hasattr(logging, expected_level_str):
                pass # It's a valid level string like "DEBUG", "INFO"
            else: # Invalid level string from config
                print(f"Warning: Invalid log level '{log_config.level}' in config, test will expect fallback INFO.")
                expected_level_str = "INFO"
        except Exception:
            print("Warning: Could not determine expected log level from config, test will expect fallback INFO.")
            expected_level_str = "INFO" # Fallback for test expectation

    expected_level_num = getattr(logging, expected_level_str, logging.INFO)

    assert root_logger_level == expected_level_num

    # Verify the formatter (more complex, requires checking a handler)
    # This part is optional as per the task description but shown for completeness.
    # We'd need to inspect the handlers on the root logger.
    if logging.getLogger().handlers:
        handler = logging.getLogger().handlers[0] # Get the first handler (usually StreamHandler from basicConfig)
        formatter = handler.formatter
        if formatter and hasattr(formatter, '_fmt'):
            expected_format = "%(levelname)s:%(name)s:%(message)s" # Assumed format
            if log_config and log_config.format:
                expected_format = log_config.format
            assert formatter._fmt == expected_format
        else:
            # If no formatter or _fmt (e.g. some custom handler), this check might not apply
            # or needs adjustment. For basicConfig's default handler, _fmt usually exists.
            pass # Could fail test here if formatter is strictly expected: pytest.fail("Formatter not as expected")
    else:
        pytest.fail("No handlers found on root logger after setup_global_logging.")

def test_log_different_levels(caplog):
    """Tests that various log levels are handled as expected."""
    setup_global_logging() # Ensure logging is set up

    log_config = config_manager.get_logging_settings()
    current_level_str = "INFO" # Fallback
    if log_config and log_config.level:
         current_level_str = log_config.level.upper()
         if not hasattr(logging, current_level_str): # Validate level string
             current_level_str = "INFO"
    current_level_num = getattr(logging, current_level_str, logging.INFO)

    logger = logging.getLogger("level_test_logger")

    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")

    if current_level_num <= logging.DEBUG:
        assert "This is a debug message." in caplog.text
    else:
        assert "This is a debug message." not in caplog.text

    if current_level_num <= logging.INFO:
        assert "This is an info message." in caplog.text
    else:
        assert "This is an info message." not in caplog.text

    if current_level_num <= logging.WARNING:
        assert "This is a warning message." in caplog.text
    else:
        assert "This is a warning message." not in caplog.text

# Example of how to run with specific app_settings.yaml for testing (if needed):
# 1. Create a temporary app_settings.yaml in a conftest.py or fixture
# 2. Point config_manager to load from there (might require modifying config_manager or using env vars)
# For now, this test relies on the existing app_settings.yaml or the fallbacks in setup_global_logging.
# To make it more robust, mocking config_manager.get_logging_settings() would be better.

@pytest.fixture
def mock_logging_config(monkeypatch):
    """Mocks config_manager.get_logging_settings() for predictable test results."""
    class MockLoggingConfig:
        def __init__(self, level, format_str):
            self.level = level
            self.format = format_str

    # Define the mock config you want for a specific test
    mock_config = MockLoggingConfig(level="DEBUG", format_str="%(levelname)s - %(name)s - TEST:%(message)s")

    def mock_get_settings():
        return mock_config

    monkeypatch.setattr(config_manager, 'get_logging_settings', mock_get_settings)
    return mock_config

def test_logging_with_mocked_config(caplog, mock_logging_config):
    """Tests logging setup with a mocked LoggingConfig."""
    setup_global_logging() # This will now use the mocked config

    # Check the confirmation message
    assert "Global logging configured successfully" in caplog.text

    test_logger = logging.getLogger("mock_config_test_logger")
    test_message = "Testing with mocked config."
    test_logger.info(test_message)

    assert f"INFO - mock_config_test_logger - TEST:{test_message}" in caplog.text # Check if format is applied

    # Verify root logger level
    assert logging.getLogger().getEffectiveLevel() == logging.DEBUG

    # Verify formatter (if possible and desired)
    if logging.getLogger().handlers:
        handler = logging.getLogger().handlers[0]
        formatter = handler.formatter
        assert formatter._fmt == mock_logging_config.format
    else:
        pytest.fail("No handlers on root logger with mocked config.")

    # Test that DEBUG messages are captured
    test_logger.debug("A debug message with mocked config.")
    assert "DEBUG - mock_config_test_logger - TEST:A debug message with mocked config." in caplog.text
