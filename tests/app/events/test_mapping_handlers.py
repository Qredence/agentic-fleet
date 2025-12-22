"""Tests for individual event mapping handlers.

This test file demonstrates the improved testability of the refactored event mapping.
Each handler can now be tested independently without going through the main dispatcher.
"""

from agent_framework._types import ChatMessage, Role
from agent_framework._workflows import (
    RequestInfoEvent,
    WorkflowStartedEvent,
    WorkflowStatusEvent,
)

from agentic_fleet.api.events.mapping import (
    _handle_request_info,
    _handle_workflow_started,
    _handle_workflow_status,
    _serialize_request_payload,
    _get_request_message,
)
from agentic_fleet.models import StreamEventType


def test_handle_workflow_started():
    """Test that WorkflowStartedEvent is always skipped."""
    event = WorkflowStartedEvent(data=None)
    result, reasoning = _handle_workflow_started(event, "previous")
    
    assert result is None
    assert reasoning == "previous"


def test_handle_workflow_status_failed():
    """Test that FAILED status converts to ERROR event."""
    event = WorkflowStatusEvent(
        state="FAILED",
        data={"message": "Test failure", "workflow_id": "test-123"}
    )
    result, reasoning = _handle_workflow_status(event, "")
    
    assert result is not None
    assert result.type == StreamEventType.ERROR
    assert result.error == "Test failure"
    assert result.data["workflow_id"] == "test-123"


def test_handle_workflow_status_in_progress():
    """Test that IN_PROGRESS status converts to progress message."""
    event = WorkflowStatusEvent(
        state="IN_PROGRESS",
        data={"message": "Starting", "workflow_id": "test-456"}
    )
    result, reasoning = _handle_workflow_status(event, "")
    
    assert result is not None
    assert result.type == StreamEventType.ORCHESTRATOR_MESSAGE
    assert result.kind == "progress"
    assert result.message == "Starting"


def test_handle_workflow_status_idle_skipped():
    """Test that IDLE and other states are skipped."""
    event = WorkflowStatusEvent(state="IDLE", data={})
    result, reasoning = _handle_workflow_status(event, "")
    
    assert result is None


def test_serialize_request_payload_with_model_dump():
    """Test serialization of Pydantic-like objects."""
    class MockRequest:
        def model_dump(self):
            return {"foo": "bar"}
    
    result = _serialize_request_payload(MockRequest())
    assert result == {"foo": "bar"}


def test_serialize_request_payload_with_dict():
    """Test serialization of dict objects."""
    result = _serialize_request_payload({"test": "value"})
    assert result == {"test": "value"}


def test_serialize_request_payload_with_none():
    """Test serialization of None."""
    result = _serialize_request_payload(None)
    assert result is None


def test_get_request_message_approval():
    """Test message selection for approval requests."""
    msg = _get_request_message("ToolApprovalRequest")
    assert msg == "Tool approval required"


def test_get_request_message_user_input():
    """Test message selection for user input requests."""
    msg = _get_request_message("UserInputRequest")
    assert msg == "User input required"


def test_get_request_message_intervention():
    """Test message selection for intervention requests."""
    msg = _get_request_message("HumanInterventionRequest")
    assert msg == "Human intervention required"


def test_get_request_message_default():
    """Test default message for unknown request types."""
    msg = _get_request_message("UnknownRequest")
    assert msg == "Action required"


def test_dispatch_table_completeness():
    """Verify all expected event types are in the dispatch table."""
    from agentic_fleet.api.events.mapping import _EVENT_HANDLERS
    
    # Core event types that should be handled
    expected_types = [
        WorkflowStartedEvent,
        WorkflowStatusEvent,
        RequestInfoEvent,
    ]
    
    for event_type in expected_types:
        assert event_type in _EVENT_HANDLERS, f"Missing handler for {event_type.__name__}"


def test_handler_isolation():
    """Test that handlers can be called independently without side effects."""
    # Create two events
    event1 = WorkflowStatusEvent(state="FAILED", data={"message": "Error 1"})
    event2 = WorkflowStatusEvent(state="FAILED", data={"message": "Error 2"})
    
    # Call handlers independently
    result1, _ = _handle_workflow_status(event1, "")
    result2, _ = _handle_workflow_status(event2, "")
    
    # Verify independence
    assert result1.error == "Error 1"
    assert result2.error == "Error 2"
    assert result1 is not result2
