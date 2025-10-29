"""Tests for EventTranslator."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from agent_framework import (
    MagenticAgentDeltaEvent,
    MagenticAgentMessageEvent,
    MagenticFinalResultEvent,
    MagenticOrchestratorMessageEvent,
    WorkflowOutputEvent,
)

from agenticfleet.api.event_translator import EventTranslator
from agenticfleet.api.models import SSEEventType


@pytest.fixture
def translator() -> EventTranslator:
    """Create an EventTranslator instance."""
    return EventTranslator()


def test_translate_orchestrator_message(translator: EventTranslator) -> None:
    """Test translating orchestrator message event."""
    # Create mock message
    mock_message = Mock()
    mock_message.text = "Planning the next steps"

    # Create event
    event = MagenticOrchestratorMessageEvent(
        kind="planning",
        message=mock_message,
    )

    sse_event = translator.translate_to_sse(event, workflow_id="test-workflow")

    assert sse_event is not None
    assert sse_event.event == SSEEventType.ORCHESTRATOR_MESSAGE
    assert sse_event.data["kind"] == "planning"
    assert sse_event.data["message"] == "Planning the next steps"
    assert sse_event.data["workflow_id"] == "test-workflow"


def test_translate_agent_delta(translator: EventTranslator) -> None:
    """Test translating agent delta event."""
    event = MagenticAgentDeltaEvent(
        agent_id="coder",
        text="def calculate_sum",
    )

    sse_event = translator.translate_to_sse(event, workflow_id="test-workflow")

    assert sse_event is not None
    assert sse_event.event == SSEEventType.AGENT_DELTA
    assert sse_event.data["agent_id"] == "coder"
    assert sse_event.data["text"] == "def calculate_sum"
    assert sse_event.data["workflow_id"] == "test-workflow"


def test_translate_agent_message(translator: EventTranslator) -> None:
    """Test translating agent message event."""
    # Create mock message
    mock_message = Mock()
    mock_message.text = "Here is the implementation..."

    event = MagenticAgentMessageEvent(
        agent_id="coder",
        message=mock_message,
    )

    sse_event = translator.translate_to_sse(event, workflow_id="test-workflow")

    assert sse_event is not None
    assert sse_event.event == SSEEventType.AGENT_MESSAGE
    assert sse_event.data["agent_id"] == "coder"
    assert sse_event.data["message"] == "Here is the implementation..."
    assert sse_event.data["workflow_id"] == "test-workflow"


def test_translate_final_result(translator: EventTranslator) -> None:
    """Test translating final result event."""
    # Create mock message
    mock_message = Mock()
    mock_message.text = "Task completed successfully"

    event = MagenticFinalResultEvent(
        message=mock_message,
    )

    sse_event = translator.translate_to_sse(event, workflow_id="test-workflow")

    assert sse_event is not None
    assert sse_event.event == SSEEventType.FINAL_RESULT
    assert sse_event.data["result"] == "Task completed successfully"
    assert sse_event.data["workflow_id"] == "test-workflow"


def test_translate_workflow_output(translator: EventTranslator) -> None:
    """Test translating workflow output event."""
    event = WorkflowOutputEvent(
        source_executor_id="test-executor",
        data={"status": "complete", "metrics": {"duration": 42}},
    )

    sse_event = translator.translate_to_sse(event, workflow_id="test-workflow")

    assert sse_event is not None
    assert sse_event.event == SSEEventType.AGENT_MESSAGE  # Currently uses agent_message
    assert sse_event.data["output"] == {"status": "complete", "metrics": {"duration": 42}}
    assert sse_event.data["workflow_id"] == "test-workflow"


def test_translate_unknown_event(translator: EventTranslator) -> None:
    """Test translating unknown event type returns None."""
    unknown_event = Mock()

    sse_event = translator.translate_to_sse(unknown_event)

    assert sse_event is None


def test_create_error_event(translator: EventTranslator) -> None:
    """Test creating error SSE event."""
    sse_event = translator.create_error_event(
        error="Something went wrong",
        workflow_id="test-workflow",
    )

    assert sse_event.event == SSEEventType.ERROR
    assert sse_event.data["error"] == "Something went wrong"
    assert sse_event.data["workflow_id"] == "test-workflow"


def test_create_error_event_from_exception(translator: EventTranslator) -> None:
    """Test creating error SSE event from exception."""
    exception = ValueError("Invalid input")

    sse_event = translator.create_error_event(error=exception)

    assert sse_event.event == SSEEventType.ERROR
    assert "Invalid input" in sse_event.data["error"]


def test_create_workflow_started_event(translator: EventTranslator) -> None:
    """Test creating workflow started SSE event."""
    sse_event = translator.create_workflow_started_event(
        workflow_id="test-workflow",
        workflow_name="Collaboration Workflow",
    )

    assert sse_event.event == SSEEventType.WORKFLOW_STARTED
    assert sse_event.data["workflow_id"] == "test-workflow"
    assert sse_event.data["workflow_name"] == "Collaboration Workflow"


def test_create_workflow_completed_event(translator: EventTranslator) -> None:
    """Test creating workflow completed SSE event."""
    sse_event = translator.create_workflow_completed_event(
        workflow_id="test-workflow",
        result="Final answer: 42",
    )

    assert sse_event.event == SSEEventType.WORKFLOW_COMPLETED
    assert sse_event.data["workflow_id"] == "test-workflow"
    assert sse_event.data["result"] == "Final answer: 42"


def test_translate_without_workflow_id(translator: EventTranslator) -> None:
    """Test translating events without workflow_id."""
    event = MagenticAgentDeltaEvent(
        agent_id="coder",
        text="test",
    )

    sse_event = translator.translate_to_sse(event)

    assert sse_event is not None
    assert "workflow_id" not in sse_event.data


def test_sse_event_to_wire_format(translator: EventTranslator) -> None:
    """Test SSE event conversion to wire format."""
    sse_event = translator.create_workflow_started_event(
        workflow_id="test",
        workflow_name="Test Workflow",
    )

    wire_format = sse_event.to_sse_format()

    assert "event: workflow.started" in wire_format
    assert "data: {" in wire_format
    assert '"workflow_id": "test"' in wire_format
    assert wire_format.endswith("\n\n")  # SSE format ends with double newline
