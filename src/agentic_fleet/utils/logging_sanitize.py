"""Utilities for sanitizing values before logging.

Removes control characters that could enable log injection or terminal escape manipulation.
Only used for log output; original identifiers (e.g., workflow IDs) are preserved internally.

Characters removed:
- Newline (\n)
- Carriage return (\r)
- Tab (\t)
- Unicode line separator (\u2028)
- Unicode paragraph separator (\u2029)
- Next line (\u0085)
- Form feed (\f)
- Vertical tab (\v)
- ESC (\x1b) - strips ANSI escape initiators

Future enhancements can introduce a logging Filter for automatic sanitization.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

REMOVED_LOG_CHARS: tuple[str, ...] = (
    "\n",
    "\r",
    "\t",
    "\u2028",
    "\u2029",
    "\u0085",
    "\f",
    "\v",
    "\x1b",
)

# Precompute translation table mapping unwanted characters to None
_SANITIZE_TRANS = {ord(ch): None for ch in REMOVED_LOG_CHARS}

__all__ = ["REMOVED_LOG_CHARS", "sanitize_log_value"]


def sanitize_log_value(value: Any) -> str:
    """Return a safe string representation for logging.

    Converts *value* to string and strips known control characters that can
    break log formatting, spoof log lines (CRLF injection), or create confusing
    terminal output with escape sequences.
    """
    try:
        s = str(value)
    except Exception as e:
        # Fallback - ensure logging never raises
        logger.debug(
            "Failed to convert value to string for logging: %s (type: %s)",
            type(value).__name__,
            e.__class__.__name__,
        )
        s = "<unrepresentable>"
    return s.translate(_SANITIZE_TRANS)
