"""Tests for progress callback utilities."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.utils.progress import (
    LoggingProgressCallback,
    NullProgressCallback,
    RichProgressCallback,
)


def test_logging_progress_callback():
    """Test LoggingProgressCallback basic functionality."""
    callback = LoggingProgressCallback(log_level=logging.INFO)

    callback.on_start("Test operation")
    assert callback.start_time is not None

    callback.on_progress("Step 1", current=1, total=5)
    callback.on_progress("Step 2", current=2, total=5)

    callback.on_complete("Test operation complete", duration=1.5)
    assert callback.start_time is None


def test_logging_progress_callback_error():
    """Test LoggingProgressCallback error handling."""
    callback = LoggingProgressCallback()

    callback.on_start("Test operation")
    callback.on_error("Test operation failed", ValueError("Test error"))
    assert callback.start_time is None


def test_null_progress_callback():
    """Test NullProgressCallback does nothing."""
    callback = NullProgressCallback()

    # Should not raise any errors
    callback.on_start("Test")
    callback.on_progress("Test", current=1, total=10)
    callback.on_complete("Test")
    callback.on_error("Test", ValueError("Error"))


def test_rich_progress_callback_without_live_context():
    """Test RichProgressCallback when no Live context is active."""
    try:
        from rich.console import Console

        console = Console()
        callback = RichProgressCallback(console=console)

        # Should create Progress instance when no Live context
        callback.on_start("Test operation")
        assert callback.progress is not None
        assert callback.task_id is not None

        callback.on_progress("Step 1", current=1, total=5)
        callback.on_complete("Test operation complete")

        assert callback.progress is None
        assert callback.task_id is None
    except ImportError:
        pytest.skip("Rich not available")


def test_rich_progress_callback_with_live_context():
    """Test RichProgressCallback falls back to logging when Live context is active."""
    try:
        from rich.console import Console

        console = Console()
        callback = RichProgressCallback(console=console)

        # Simulate Live context by adding to _live_stack
        mock_live = MagicMock()
        console._live_stack = [mock_live]

        # Should use logging instead of Progress bars
        callback.on_start("Test operation")
        assert callback.progress is None  # Should not create Progress

        callback.on_progress("Step 1", current=1, total=5)
        callback.on_complete("Test operation complete")
    except ImportError:
        pytest.skip("Rich not available")


def test_rich_progress_callback_fallback_on_error():
    """Test RichProgressCallback falls back to logging on Progress creation error."""
    try:
        from rich.console import Console

        console = Console()
        callback = RichProgressCallback(console=console)

        # Mock Progress to raise an error
        with patch.object(callback, "Progress", side_effect=Exception("Progress error")):
            callback.on_start("Test operation")
            # Should fall back to logging callback
            assert callback.progress is None
    except ImportError:
        pytest.skip("Rich not available")


def test_get_default_progress_callback():
    """Test get_default_progress_callback returns appropriate callback."""
    from agentic_fleet.utils.progress import get_default_progress_callback

    callback = get_default_progress_callback(use_rich=True)
    # Should return RichProgressCallback if Rich is available, otherwise LoggingProgressCallback
    assert callback is not None

    callback = get_default_progress_callback(use_rich=False)
    assert isinstance(callback, LoggingProgressCallback)
