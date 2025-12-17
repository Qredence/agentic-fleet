import logging
import os
from unittest.mock import patch

from agentic_fleet.utils.cfg import env_config
from agentic_fleet.utils.logger import setup_logger


def test_setup_logger_defaults():
    logger = setup_logger("test_logger")
    assert logger.name == "test_logger"
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)


def test_setup_logger_json():
    logger = setup_logger("json_logger", json_format=True)
    handler = logger.handlers[0]
    # Check if formatter is JsonFormatter
    assert "JsonFormatter" in str(type(handler.formatter))


def test_setup_logger_file(tmp_path):
    log_file = tmp_path / "test.log"
    logger = setup_logger("file_logger", log_file=str(log_file))
    assert len(logger.handlers) == 2
    assert isinstance(logger.handlers[1], logging.FileHandler)

    logger.info("test message")
    # Force flush
    for handler in logger.handlers:
        handler.flush()

    assert log_file.exists()
    content = log_file.read_text()
    assert "test message" in content


def test_setup_logger_env_override():
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        # Clear the cached env values so the patched env var is read
        env_config.clear_cache()
        logger = setup_logger("env_logger")
        handler = logger.handlers[0]
        assert "JsonFormatter" in str(type(handler.formatter))
