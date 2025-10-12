"""Logging configuration for AgenticFleet."""

import logging
import os
import re
import sys
from pathlib import Path


def _secure_filename(filename: str) -> str:
    """
    Sanitize a filename to remove potentially dangerous characters.

    This is a lightweight replacement for werkzeug.utils.secure_filename
    that removes path separators and other unsafe characters.

    Args:
        filename: The filename to sanitize

    Returns:
        A safe filename with only alphanumeric, dash, underscore, and dot
    """
    # Remove any path components
    filename = os.path.basename(filename)
    # Replace whitespace with underscores
    filename = re.sub(r"\s+", "_", filename)
    # Keep only safe characters
    filename = re.sub(r"[^a-zA-Z0-9._-]", "", filename)
    return filename


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    format_string: str | None = None,
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        format_string: Optional custom format string
    """
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        # Only allow log files within the default logs directory
        logs_root = Path("logs").resolve()
        candidate_path = Path(log_file)
        # Forbid absolute paths or parent traversal
        if candidate_path.is_absolute() or ".." in candidate_path.parts:
            msg = (
                f"Log file path '{candidate_path}' is not allowed: "
                f"must be a simple filename inside '{logs_root}' "
                "(no absolute path or parent traversal)"
            )
            raise ValueError(msg)
        # Restrict to safe filename only
        safe_filename = _secure_filename(candidate_path.name)
        if not safe_filename:
            msg = (
                f"Log file path '{candidate_path}' is not allowed: "
                "filename has no valid characters after sanitization"
            )
            raise ValueError(msg)
        log_path = (logs_root / safe_filename).resolve()
        # Final containment check
        try:
            inside_logs = (
                log_path.is_relative_to(logs_root)
                if hasattr(log_path, "is_relative_to")
                else os.path.commonpath(
                    [str(log_path), str(logs_root)]
                ) == str(logs_root)
            )
        except Exception:
            inside_logs = False
        if not inside_logs:
            msg = (
                f"Log file path '{log_path}' is not allowed: "
                f"must be within '{logs_root}'"
            )
            raise ValueError(msg)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(str(log_path)))

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=handlers,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
