"""
Logging utilities for the workflow system.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from pythonjsonlogger import jsonlogger

from .env import env_config


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
    Setup logger with console and optional file output.

    Args:
        name: Logger name
        level: Logging level
        log_file: Optional path to log file
        format_string: Optional format string for text logs
        json_format: Whether to use JSON formatting (overrides format_string)
    """
    # Check env var for global JSON logging override
    if env_config.log_format == "json":
        json_format = True

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Prevent propagation to root logger to avoid duplicate output
    logger.propagate = False

    # Remove existing handlers to prevent duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    if not any(isinstance(f, _EnsureRequestIdFilter) for f in logger.filters):
        logger.addFilter(_EnsureRequestIdFilter())

    # Create formatter
    if json_format:
        formatter = jsonlogger.JsonFormatter(
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
