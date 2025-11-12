"""Unit tests for WorkflowEventBridge enhancements."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from agentic_fleet.workflow.events import WorkflowEventBridge


def test_convert_event_default_behavior() -> None:
    """Test convert_event maintains backward compatibility with unknown events."""
    # Test with unknown event type
    unknown_event = Mock()
    unknown_event.__class__.__name__ = "UnknownEvent"

    result = WorkflowEventBridge.convert_event(unknown_event, openai_format=False)

    assert result["type"] == "unknown"
    assert "raw" in result["data"]
    assert "openai_type" not in result


def test_convert_event_openai_format_flag() -> None:
    """Test convert_event with openai_format flag doesn't break on unknown events."""
    # Test with unknown event type
    unknown_event = Mock()
    unknown_event.__class__.__name__ = "UnknownEvent"

    result = WorkflowEventBridge.convert_event(unknown_event, openai_format=True)

    assert result["type"] == "unknown"
    # Should still work even with openai_format flag


def test_unknown_event_handling() -> None:
    """Test unknown event types are handled gracefully."""
    unknown_event = Mock()
    unknown_event.__class__.__name__ = "UnknownEvent"

    result = WorkflowEventBridge.convert_event(unknown_event)

    assert result["type"] == "unknown"
    assert "raw" in result["data"]
    assert result["data"]["event_type"] == "UnknownEvent"


def test_event_with_none_text() -> None:
    """Test event handling when text is None."""
    # Test with unknown event that has None text
    unknown_event = Mock()
    unknown_event.__class__.__name__ = "UnknownEvent"
    unknown_event.text = None

    result = WorkflowEventBridge.convert_event(unknown_event)

    assert result["type"] == "unknown"
    assert "raw" in result["data"]


def test_event_with_none_message() -> None:
    """Test event handling when message is None."""
    # Test with unknown event that has None message
    unknown_event = Mock()
    unknown_event.__class__.__name__ = "UnknownEvent"
    unknown_event.message = None

    result = WorkflowEventBridge.convert_event(unknown_event)

    assert result["type"] == "unknown"
    assert "raw" in result["data"]


def test_event_bridge_handles_missing_event_types() -> None:
    """Test event bridge handles missing event types gracefully."""
    # When event types are not available (ImportError scenario)
    unknown_event = Mock()
    unknown_event.__class__.__name__ = "SomeEvent"

    result = WorkflowEventBridge.convert_event(unknown_event)

    assert result["type"] == "unknown"
    assert "raw" in result["data"]


def test_agent_run_update_emits_reasoning_delta() -> None:
    """Agent run updates with reasoning content should yield reasoning delta events."""

    agent_framework = pytest.importorskip("agent_framework")
    update = agent_framework.AgentRunResponseUpdate(
        run_id="run-1",
        response_id="resp-1",
        contents=[agent_framework.TextReasoningContent(text="Step 1")],
    )
    event = agent_framework.AgentRunUpdateEvent(executor_id="agent_planner", data=update)

    result = WorkflowEventBridge.convert_event(event, openai_format=True)

    assert result["type"] == "reasoning.delta"
    data = result["data"]
    assert isinstance(data, dict)
    assert data["delta"] == "Step 1"
    assert data["agent_id"] == "planner"
    assert result.get("openai_type") == "reasoning.delta"
