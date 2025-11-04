"""Tests for utils.events module."""

from __future__ import annotations

from agentic_fleet.models.events import WorkflowEvent
from agentic_fleet.utils.events import EventHandler


def test_log_event() -> None:
    """Test EventHandler.log_event logs events."""
    event: WorkflowEvent = {"type": "message.delta", "data": {"delta": "test"}}
    # Should not raise
    EventHandler.log_event(event)


def test_is_completion_event() -> None:
    """Test is_completion_event identifies completion events."""
    completion_event: WorkflowEvent = {"type": "message.done", "data": {}}
    delta_event: WorkflowEvent = {"type": "message.delta", "data": {"delta": "test"}}

    assert EventHandler.is_completion_event(completion_event) is True
    assert EventHandler.is_completion_event(delta_event) is False


def test_is_error_event() -> None:
    """Test is_error_event identifies error events."""
    error_event: WorkflowEvent = {"type": "error", "data": {"error": "test"}}
    delta_event: WorkflowEvent = {"type": "message.delta", "data": {"delta": "test"}}

    assert EventHandler.is_error_event(error_event) is True
    assert EventHandler.is_error_event(delta_event) is False


def test_extract_delta() -> None:
    """Test extract_delta extracts delta text from events."""
    delta_event: WorkflowEvent = {"type": "message.delta", "data": {"delta": "Hello World"}}
    non_delta_event: WorkflowEvent = {"type": "message.done", "data": {}}

    assert EventHandler.extract_delta(delta_event) == "Hello World"
    assert EventHandler.extract_delta(non_delta_event) == ""


def test_extract_delta_empty_delta() -> None:
    """Test extract_delta handles empty delta."""
    delta_event: WorkflowEvent = {"type": "message.delta", "data": {"delta": ""}}

    assert EventHandler.extract_delta(delta_event) == ""
