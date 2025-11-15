"""Error sanitization utilities for user-facing error messages."""

from __future__ import annotations

import logging
import traceback
from typing import Any

logger = logging.getLogger(__name__)

# Maximum length for task content in error messages
MAX_TASK_PREVIEW_LENGTH = 100
MAX_ERROR_MESSAGE_LENGTH = 500


def sanitize_error_message(
    error: Exception,
    task: str | None = None,
    include_details: bool = False,
) -> str:
    """
    Create a sanitized, user-friendly error message.

    Args:
        error: The exception that occurred
        task: Optional task string that should be sanitized
        include_details: Whether to include more details (for debugging)

    Returns:
        Sanitized error message safe for user-facing output
    """
    error_type = type(error).__name__
    error_msg = str(error)

    # Log full error details server-side
    logger.error(
        "Error occurred: %s: %s",
        error_type,
        error_msg,
        exc_info=True,
    )

    # Sanitize task content if provided
    task_preview = ""
    if task:
        if len(task) > MAX_TASK_PREVIEW_LENGTH:
            task_preview = f"{task[:MAX_TASK_PREVIEW_LENGTH]}..."
        else:
            task_preview = task

    # Create user-friendly message
    if include_details:
        # Include more details for debugging
        message = f"{error_type}: {error_msg}"
        if task_preview:
            message += f" (task: {task_preview})"
    else:
        # Generic message for production
        lowered_type = error_type.lower()
        lowered_msg = error_msg.lower()
        if "api" in lowered_type or "key" in lowered_msg:
            message = "Configuration error: Please check your API keys and configuration."
        elif "timeout" in lowered_msg or "timeout" in lowered_type:
            message = "Request timed out. The task may be too complex or the service may be busy."
        elif "connection" in lowered_msg or "network" in lowered_msg:
            message = "Network error: Unable to connect to the service. Please try again."
        elif "validation" in lowered_type or "invalid" in lowered_msg:
            message = "Invalid input: Please check your request and try again."
        else:
            message = "An error occurred while processing your request. Please try again."

    # Truncate if too long
    if len(message) > MAX_ERROR_MESSAGE_LENGTH:
        message = message[:MAX_ERROR_MESSAGE_LENGTH] + "..."

    return message


def sanitize_task_content(task: str, max_length: int = MAX_TASK_PREVIEW_LENGTH) -> str:
    """
    Sanitize task content for display in error messages.

    Args:
        task: Task string to sanitize
        max_length: Maximum length for preview

    Returns:
        Sanitized task preview
    """
    if not task:
        return ""

    # Remove potentially sensitive patterns
    sanitized = task.strip()

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized


def log_error_with_context(
    error: Exception,
    context: dict[str, Any] | None = None,
    task: str | None = None,
) -> None:
    """
    Log error with full context for server-side debugging.

    Args:
        error: The exception that occurred
        context: Additional context dictionary
        task: Optional task string
    """
    error_details: dict[str, Any] = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
    }

    if task:
        error_details["task_preview"] = sanitize_task_content(task, max_length=200)

    if context:
        error_details["context"] = context

    logger.error("Error with context: %s", error_details, exc_info=True)


def create_user_facing_error(
    error: Exception,
    task: str | None = None,
    error_code: str | None = None,
) -> dict[str, Any]:
    """
    Create a structured error response for user-facing output.

    Args:
        error: The exception that occurred
        task: Optional task string
        error_code: Optional error code for programmatic handling

    Returns:
        Dictionary with sanitized error information
    """
    # Log full error server-side
    log_error_with_context(error, task=task)

    # Create sanitized response
    response: dict[str, Any] = {
        "error": sanitize_error_message(error, task=task, include_details=False),
        "error_type": type(error).__name__,
    }

    if error_code:
        response["error_code"] = error_code

    return response


__all__ = [
    "create_user_facing_error",
    "log_error_with_context",
    "sanitize_error_message",
    "sanitize_task_content",
]
