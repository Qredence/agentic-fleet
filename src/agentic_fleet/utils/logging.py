"""Logging setup and utilities."""

from __future__ import annotations

import logging
import os


def setup_logging(level: str | int | None = None) -> None:
    """Configure console-friendly logging.

    Args:
        level: Logging level (string like "INFO", "DEBUG", or logging constant).
            If None, uses LOG_LEVEL environment variable or defaults to INFO.
    """
    if level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        numeric_level = getattr(logging, log_level, logging.INFO)
    elif isinstance(level, str):
        numeric_level = getattr(logging, level.upper(), logging.INFO)
    else:
        numeric_level = level

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,  # Override any existing configuration
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured at {logging.getLevelName(numeric_level)} level")
