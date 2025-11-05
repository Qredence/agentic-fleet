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


def sanitize_for_log(value: str) -> str:
    """Sanitize string for safe logging: remove all ASCII control characters and mark user input clearly.

    Strips ASCII control characters (0x00-0x1F, 0x7F), newlines, carriage returns, Unicode line/paragraph
    separators, NEL, and escape codes. Encloses user input in <angle brackets> to prevent log confusion.

    Args:
        value: String to sanitize

    Returns:
        Sanitized and clearly marked string
    """
    to_clean = value if isinstance(value, str) else str(value)
    # Build translation table for ASCII controls (0-31, 127) + documented Unicode separators
    controls = "".join(chr(i) for i in range(0, 32)) + chr(0x7F) + "\u2028\u2029\u0085"
    cleaned = to_clean.translate(str.maketrans("", "", controls))
    # Enclose the sanitized input in angle brackets for visibility
    return f"<{cleaned}>"
