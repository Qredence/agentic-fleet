"""Logging configuration for AgenticFleet."""

import logging
import sys
from pathlib import Path
import os

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
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        # Only allow log files within the default logs directory
        logs_root = Path("logs").resolve()
        candidate_path = Path(log_file)
        log_path = (logs_root / candidate_path).resolve() if not candidate_path.is_absolute() else candidate_path.resolve()
        # Check that log_path is inside logs_root
        try:
            # Python 3.9+: use is_relative_to, else fallback
            inside_logs = log_path.is_relative_to(logs_root) if hasattr(log_path, "is_relative_to") else str(log_path).startswith(str(logs_root))
        except Exception:
            inside_logs = False
        if not inside_logs:
            raise ValueError(f"Log file path '{log_path}' is not allowed: must be within '{logs_root}'")
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
