import json
import logging
from io import StringIO

from agentic_fleet.utils.logger import setup_logger


def test_json_logger_formatting():
    # Capture stdout
    stream = StringIO()

    # Force JSON format via argument
    logger = setup_logger("test_json", log_file=None, json_format=True)

    # Replace the stream handler's stream with our capture stream
    # (setup_logger adds a StreamHandler to sys.stdout by default)
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.stream = stream

    logger.info("Test message", extra={"request_id": "123"})

    output = stream.getvalue()
    assert output, "Logger should produce output"

    try:
        log_record = json.loads(output)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Output is not valid JSON: {output}") from exc

    assert log_record["message"] == "Test message"
    assert log_record["levelname"] == "INFO"
    assert log_record["name"] == "test_json"
    assert log_record["request_id"] == "123"
    assert "asctime" in log_record


def test_env_var_override(monkeypatch):
    monkeypatch.setenv("LOG_FORMAT", "json")

    logger = setup_logger("test_env", log_file=None)

    # Check if the formatter is a JsonFormatter
    handler = logger.handlers[0]
    # Note: We check the class name string to avoid importing pythonjsonlogger in test if not needed
    assert "JsonFormatter" in handler.formatter.__class__.__name__
