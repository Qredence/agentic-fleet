"""
Tests for SSE event integration between frontend and backend.
"""

import json

from agenticfleet.haxui.sse_events import (
    AgentResponseEvent,
    ApprovalRequestEvent,
    CompleteEvent,
    ErrorEvent,
    EventType,
    ProgressEvent,
    RiskLevel,
    SSEEventEmitter,
    ToolCallEvent,
)
from agenticfleet.haxui.web_approval import assess_risk_level, create_approval_request


class TestSSEEventModels:
    """Test Pydantic models for SSE events."""

    def test_agent_response_event(self) -> None:
        """Test AgentResponseEvent creation and serialization."""
        event = AgentResponseEvent(agent="orchestrator", content="Test response", isComplete=False)

        assert event.type == EventType.AGENT_RESPONSE
        assert event.agent == "orchestrator"
        assert event.content == "Test response"
        assert event.isComplete is False
        assert event.timestamp > 0

        # Test SSE formatting
        sse_output = event.to_sse()
        sse_str = sse_output.decode()
        assert sse_str.startswith("data: ")
        assert sse_str.endswith("\n\n")

        # Parse JSON from SSE output
        json_str = sse_str.replace("data: ", "").strip()
        parsed = json.loads(json_str)
        assert parsed["type"] == "agent_response"
        assert parsed["agent"] == "orchestrator"

    def test_tool_call_event(self) -> None:
        """Test ToolCallEvent creation and serialization."""
        event = ToolCallEvent(tool="web_search", args={"query": "test"}, result={"found": True})

        assert event.type == EventType.TOOL_CALL
        assert event.tool == "web_search"
        assert event.args["query"] == "test"
        assert event.result is not None
        assert event.result["found"] is True

    def test_approval_request_event(self) -> None:
        """Test ApprovalRequestEvent with risk levels."""
        event = ApprovalRequestEvent(
            id="req-123",
            operation="code_execution",
            params={"code": 'print("hello")'},
            context="Execute test code",
            risk_level=RiskLevel.LOW,
        )

        assert event.type == EventType.APPROVAL_REQUEST
        assert event.id == "req-123"
        assert event.operation == "code_execution"
        assert event.risk_level == RiskLevel.LOW

        sse_output = event.to_sse()
        sse_str = sse_output.decode()
        parsed = json.loads(sse_str.replace("data: ", "").strip())
        assert parsed["risk_level"] == "low"

    def test_progress_event(self) -> None:
        """Test ProgressEvent with progress clamping."""
        event = ProgressEvent(step="analyzing", progress=0.75, message="Analyzing data...")

        assert event.type == EventType.PROGRESS
        assert event.progress == 0.75
        assert 0.0 <= event.progress <= 1.0

    def test_error_event(self) -> None:
        """Test ErrorEvent with recoverability."""
        event = ErrorEvent(
            error="API rate limit",
            details="OpenAI returned 429",
            recoverable=True,
        )

        assert event.type == EventType.ERROR
        assert event.error == "API rate limit"
        assert event.recoverable is True

    def test_complete_event(self) -> None:
        """Test CompleteEvent with result payload."""
        event = CompleteEvent(result={"answer": "42"}, summary="Task completed successfully")

        assert event.type == EventType.COMPLETE
        assert event.result["answer"] == "42"
        assert event.summary == "Task completed successfully"


class TestSSEEventEmitter:
    """Test SSEEventEmitter utility methods."""

    def test_emit_agent_response(self) -> None:
        """Test emitting agent response events."""
        sse_output = SSEEventEmitter.emit_agent_response(
            agent="coder", content="Writing code...", is_complete=False
        )

        sse_str = sse_output.decode()
        assert sse_str.startswith("data: ")
        parsed = json.loads(sse_str.replace("data: ", "").strip())
        assert parsed["type"] == "agent_response"
        assert parsed["agent"] == "coder"
        assert parsed["content"] == "Writing code..."
        assert parsed["isComplete"] is False

    def test_emit_tool_call(self) -> None:
        """Test emitting tool call events."""
        sse_output = SSEEventEmitter.emit_tool_call(
            tool="code_interpreter", args={"code": "x = 1"}, result={"success": True}
        )

        parsed = json.loads(sse_output.decode().replace("data: ", "").strip())
        assert parsed["type"] == "tool_call"
        assert parsed["tool"] == "code_interpreter"
        assert parsed["result"]["success"] is True

    def test_emit_approval_request(self) -> None:
        """Test emitting approval request events with risk level."""
        sse_output = SSEEventEmitter.emit_approval_request(
            id="approval-456",
            operation="file_write",
            params={"path": "/tmp/test.txt", "content": "data"},
            context="Write test file",
            risk_level=RiskLevel.MEDIUM,
        )

        parsed = json.loads(sse_output.decode().replace("data: ", "").strip())
        assert parsed["type"] == "approval_request"
        assert parsed["id"] == "approval-456"
        assert parsed["operation"] == "file_write"
        assert parsed["risk_level"] == "medium"

    def test_emit_progress(self) -> None:
        """Test emitting progress events with clamping."""
        # Test normal progress
        sse_output = SSEEventEmitter.emit_progress(
            step="processing", progress=0.5, message="Processing..."
        )

        parsed = json.loads(sse_output.decode().replace("data: ", "").strip())
        assert parsed["type"] == "progress"

        # Test progress clamping (>1.0)
        sse_output = SSEEventEmitter.emit_progress(step="done", progress=1.5, message="Complete")

        parsed = json.loads(sse_output.decode().replace("data: ", "").strip())
        assert parsed["progress"] == 1.0

        # Test progress clamping (<0.0)
        sse_output = SSEEventEmitter.emit_progress(step="start", progress=-0.5, message="Starting")

        parsed = json.loads(sse_output.decode().replace("data: ", "").strip())
        assert parsed["progress"] == 0.0

    def test_emit_error(self) -> None:
        """Test emitting error events."""
        sse_output = SSEEventEmitter.emit_error(
            error="Test error", details="Error details", recoverable=True
        )

        parsed = json.loads(sse_output.decode().replace("data: ", "").strip())
        assert parsed["type"] == "error"
        assert parsed["error"] == "Test error"
        assert parsed["recoverable"] is True

    def test_emit_complete(self) -> None:
        """Test emitting completion events."""
        sse_output = SSEEventEmitter.emit_complete(
            result={"status": "success", "data": [1, 2, 3]}, summary="Completed task"
        )

        parsed = json.loads(sse_output.decode().replace("data: ", "").strip())
        assert parsed["type"] == "complete"
        assert parsed["result"]["status"] == "success"
        assert parsed["summary"] == "Completed task"


class TestRiskAssessment:
    """Test risk level assessment logic."""

    def test_high_risk_operations(self) -> None:
        """Test high-risk operation detection."""
        assert assess_risk_level("file_write") == RiskLevel.HIGH
        assert assess_risk_level("file_delete") == RiskLevel.HIGH
        assert assess_risk_level("system_command") == RiskLevel.HIGH
        assert assess_risk_level("network_request") == RiskLevel.HIGH

    def test_medium_risk_operations(self) -> None:
        """Test medium-risk operation detection."""
        assert assess_risk_level("code_execution") == RiskLevel.MEDIUM
        assert assess_risk_level("database_query") == RiskLevel.MEDIUM
        assert assess_risk_level("plan_review") == RiskLevel.MEDIUM

    def test_sensitive_content_elevation(self) -> None:
        """Test risk elevation for sensitive content."""
        # Should elevate to high due to sensitive keyword
        assert (
            assess_risk_level("code_execution", details={"code": 'api_key = "secret_password"'})
            == RiskLevel.HIGH
        )

        assert assess_risk_level("file_read", details={"path": "/etc/passwd"}) == RiskLevel.HIGH

        # Should remain medium without sensitive content
        assert (
            assess_risk_level("code_execution", details={"code": 'print("hello")'})
            == RiskLevel.MEDIUM
        )

    def test_low_risk_default(self) -> None:
        """Test default low risk for unknown operations."""
        assert assess_risk_level("web_search") == RiskLevel.LOW
        assert assess_risk_level("data_analysis") == RiskLevel.LOW
        assert assess_risk_level("unknown_operation") == RiskLevel.LOW


class TestApprovalRequestCreation:
    """Test approval request creation with risk assessment."""

    def test_create_with_automatic_risk_assessment(self) -> None:
        """Test creating approval request with automatic risk assessment."""
        request = create_approval_request(
            agent_name="coder",
            operation_type="code_execution",
            operation="Execute Python code",
            details={"code": 'print("test")'},
        )

        assert request.agent_name == "coder"
        assert request.operation_type == "code_execution"
        assert request.details["risk_level"] == "medium"  # Auto-assessed
        assert "code" in request.details

    def test_create_with_explicit_risk_level(self) -> None:
        """Test creating approval request with explicit risk override."""
        request = create_approval_request(
            agent_name="coder",
            operation_type="web_search",
            operation="Search the web",
            details={"query": "test"},
            risk_level=RiskLevel.HIGH,  # Explicitly set
        )

        assert request.details["risk_level"] == "high"  # Override applied

    def test_create_high_risk_with_sensitive_content(self) -> None:
        """Test that sensitive content triggers high risk."""
        request = create_approval_request(
            agent_name="coder",
            operation_type="code_execution",
            operation="Execute code with API key",
            details={"code": 'key = "secret_api_key_12345"'},
        )

        assert request.details["risk_level"] == "high"  # Elevated due to sensitive keyword

    def test_request_id_uniqueness(self) -> None:
        """Test that each request gets a unique ID."""
        request1 = create_approval_request(
            agent_name="test", operation_type="test_op", operation="Test"
        )

        request2 = create_approval_request(
            agent_name="test", operation_type="test_op", operation="Test"
        )

        assert request1.request_id != request2.request_id
