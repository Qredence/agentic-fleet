"""Tests for error sanitization utilities."""

from __future__ import annotations

from agentic_fleet.utils.error_utils import (
    create_user_facing_error,
    sanitize_error_message,
    sanitize_task_content,
)


def test_sanitize_error_message_generic():
    """Test sanitization of generic error messages."""
    error = ValueError("Something went wrong")
    message = sanitize_error_message(error)

    assert "error occurred" in message.lower()
    assert "Something went wrong" not in message  # Should be generic


def test_sanitize_error_message_with_task():
    """Test sanitization with task content."""
    error = ValueError("Processing failed")
    task = "This is a very long task that contains sensitive information that should not be exposed"
    message = sanitize_error_message(error, task=task)

    assert len(message) <= 500  # Should be truncated
    assert len(task) > len(message)  # Task should be truncated


def test_sanitize_error_message_api_key():
    """Test that API key errors are handled appropriately."""
    error = ValueError("Invalid API key")
    message = sanitize_error_message(error)

    assert "api" in message.lower() or "configuration" in message.lower()


def test_sanitize_error_message_timeout():
    """Test that timeout errors are handled appropriately."""
    error = TimeoutError("Request timed out")
    message = sanitize_error_message(error)

    assert "timeout" in message.lower() or "timed out" in message.lower()


def test_sanitize_task_content():
    """Test task content sanitization."""
    long_task = "A" * 200
    sanitized = sanitize_task_content(long_task, max_length=100)

    assert len(sanitized) <= 103  # 100 + "..."
    assert sanitized.endswith("...")


def test_sanitize_task_content_short():
    """Test sanitization of short task content."""
    short_task = "Short task"
    sanitized = sanitize_task_content(short_task)

    assert sanitized == short_task


def test_create_user_facing_error():
    """Test creation of user-facing error response."""
    error = ValueError("Test error")
    response = create_user_facing_error(error, error_code="TEST_ERROR")

    assert "error" in response
    assert "error_type" in response
    assert "error_code" in response
    assert response["error_code"] == "TEST_ERROR"
    assert "Test error" not in response["error"]  # Should be sanitized


def test_create_user_facing_error_with_task():
    """Test user-facing error with task content."""
    error = ValueError("Processing failed")
    task = "Sensitive task information"
    response = create_user_facing_error(error, task=task)

    assert "error" in response
    # Task should not appear in full
    assert task not in response["error"]
