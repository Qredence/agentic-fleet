"""
Logging utilities for the workflow system.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from pythonjsonlogger import jsonlogger  # type: ignore[import]

from .cfg import env_config


class _EnsureRequestIdFilter(logging.Filter):
    """Guarantee `request_id` exists so formatters don't raise KeyError."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
        if not hasattr(record, "request_id"):
            record.request_id = None
        return True


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: str | None = None,
    format_string: str | None = None,
    json_format: bool = False,
) -> logging.Logger:
    """
    Configure and return a logger with console output and optional file output, supporting plain-text or JSON log formats.

    Parameters:
        name (str): Logger name.
        level (str): Logging level name (e.g., "INFO", "DEBUG").
        log_file (str | None): Path to a file to also write logs to; when None, file logging is disabled.
        format_string (str | None): Text-format string for log messages; ignored when `json_format` is True.
        json_format (bool): If True, use JSON-formatted logs. If the environment config `env_config.log_format` equals "json", JSON formatting is forced regardless of this argument.

    Returns:
        logging.Logger: A logger configured with a console handler (and optional file handler), an appropriate formatter (JSON or text), an added request_id filter to ensure `request_id` exists on records, cleared duplicate handlers, and propagation disabled.
    """
    # Check env var for global JSON logging override
    if env_config.log_format == "json":
        json_format = True

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Suppress DSPy adapter fallback warnings (expected behavior when model
    # doesn't support structured outputs - graceful fallback to JSON mode)
    logging.getLogger("dspy.adapters.json_adapter").setLevel(logging.ERROR)

    # Prevent propagation to root logger to avoid duplicate output
    logger.propagate = False

    # Remove existing handlers to prevent duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    if not any(isinstance(f, _EnsureRequestIdFilter) for f in logger.filters):
        logger.addFilter(_EnsureRequestIdFilter())

    # Create formatter
    if json_format:
        formatter = jsonlogger.JsonFormatter(  # type: ignore[attr-defined]
            "%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s",
            timestamp=True,
        )
    else:
        if format_string is None:
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
