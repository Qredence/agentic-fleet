"""
Logging utilities for the workflow system.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: str | None = None,
    format_string: str | None = None,
) -> logging.Logger:
    """
    Setup logger with console and optional file output.
    """

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Default format
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
