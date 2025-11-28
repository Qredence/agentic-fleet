"""Tests for the streaming SSE endpoint.

Tests cover:
- SSE event format and parsing
- Event type mapping from workflow events
- Reasoning delta emission
- Per-request reasoning_effort override
- Concurrent workflow limit (429 status)
- Session lifecycle management
- Error handling with reasoning_partial flag
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from agentic_fleet.app.dependencies import WorkflowSessionManager
from agentic_fleet.app.main import app
from agentic_fleet.app.schemas import ChatRequest, StreamEvent, StreamEventType, WorkflowStatus


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def session_manager():
    """Create a fresh session manager."""
    return WorkflowSessionManager(max_concurrent=2)


class TestStreamEventSchema:
    """Tests for StreamEvent Pydantic model."""

    def test_to_sse_dict_minimal(self):
        """Test SSE dict conversion with minimal fields."""
        event = StreamEvent(type=StreamEventType.DONE)
        result = event.to_sse_dict()

        assert result["type"] == "done"
        assert "timestamp" in result
        assert "message" not in result
        assert "delta" not in result

    def test_to_sse_dict_full(self):
        """Test SSE dict conversion with all fields."""
        event = StreamEvent(
            type=StreamEventType.RESPONSE_DELTA,
            delta="Hello",
            agent_id="researcher",
            kind="progress",
        )
        result = event.to_sse_dict()

        assert result["type"] == "response.delta"
        assert result["delta"] == "Hello"
        assert result["agent_id"] == "researcher"
        assert result["kind"] == "progress"

    def test_to_sse_dict_reasoning(self):
        """Test SSE dict with reasoning fields."""
        event = StreamEvent(
            type=StreamEventType.REASONING_DELTA,
            reasoning="Let me think about this...",
            agent_id="analyst",
        )
        result = event.to_sse_dict()

        assert result["type"] == "reasoning.delta"
        assert result["reasoning"] == "Let me think about this..."
        assert result["agent_id"] == "analyst"

    def test_to_sse_dict_error_with_partial(self):
        """Test SSE dict for error with reasoning_partial flag."""
        event = StreamEvent(
            type=StreamEventType.ERROR,
            error="Connection timeout",
            reasoning_partial=True,
        )
        result = event.to_sse_dict()

        assert result["type"] == "error"
        assert result["error"] == "Connection timeout"
        assert result["reasoning_partial"] is True


class TestWorkflowSessionManager:
    """Tests for session manager functionality."""

    def test_create_session(self, session_manager):
        """Test session creation."""
        session = session_manager.create_session(
            task="Test task",
            reasoning_effort="medium",
        )

        assert session.workflow_id.startswith("wf-")
        assert session.task == "Test task"
        assert session.status == WorkflowStatus.CREATED
        assert session.reasoning_effort == "medium"
        assert isinstance(session.created_at, datetime)

    def test_get_session(self, session_manager):
        """Test retrieving a session."""
        created = session_manager.create_session(task="Test")
        retrieved = session_manager.get_session(created.workflow_id)

        assert retrieved is not None
        assert retrieved.workflow_id == created.workflow_id

    def test_get_session_not_found(self, session_manager):
        """Test retrieving non-existent session."""
        result = session_manager.get_session("wf-nonexistent")
        assert result is None

    def test_update_status(self, session_manager):
        """Test status update."""
        session = session_manager.create_session(task="Test")
        now = datetime.now()

        session_manager.update_status(
            session.workflow_id,
            WorkflowStatus.RUNNING,
            started_at=now,
        )

        updated = session_manager.get_session(session.workflow_id)
        assert updated is not None
        assert updated.status == WorkflowStatus.RUNNING
        assert updated.started_at == now

    def test_count_active(self, session_manager):
        """Test counting active workflows."""
        assert session_manager.count_active() == 0

        s1 = session_manager.create_session(task="Task 1")
        assert session_manager.count_active() == 1

        session_manager.create_session(task="Task 2")  # s2 not needed
        assert session_manager.count_active() == 2

        session_manager.update_status(s1.workflow_id, WorkflowStatus.COMPLETED)
        assert session_manager.count_active() == 1

    def test_concurrent_limit_enforced(self, session_manager):
        """Test that concurrent limit raises 429."""
        from fastapi import HTTPException

        # Create max sessions
        session_manager.create_session(task="Task 1")
        session_manager.create_session(task="Task 2")

        # Third should fail
        with pytest.raises(HTTPException, match="Maximum concurrent"):
            session_manager.create_session(task="Task 3")

    def test_list_sessions(self, session_manager):
        """Test listing all sessions."""
        session_manager.create_session(task="Task 1")
        session_manager.create_session(task="Task 2")

        sessions = session_manager.list_sessions()
        assert len(sessions) == 2

    def test_cleanup_completed(self, session_manager):
        """Test cleanup of old completed sessions."""
        s1 = session_manager.create_session(task="Task 1")
        session_manager.update_status(s1.workflow_id, WorkflowStatus.COMPLETED)

        # Mock old timestamp
        session = session_manager.get_session(s1.workflow_id)
        if session:
            session.created_at = datetime(2020, 1, 1)  # Very old

        cleaned = session_manager.cleanup_completed(max_age_seconds=60)
        assert cleaned == 1
        assert session_manager.get_session(s1.workflow_id) is None


class TestChatRequest:
    """Tests for ChatRequest validation."""

    def test_valid_request(self):
        """Test valid request creation."""
        request = ChatRequest(
            message="Hello",
            stream=True,
            reasoning_effort="medium",
        )
        assert request.message == "Hello"
        assert request.stream is True
        assert request.reasoning_effort == "medium"

    def test_empty_message_rejected(self):
        """Test that empty message is rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="String should have at least 1"):
            ChatRequest(message="")

    def test_default_values(self):
        """Test default values."""
        request = ChatRequest(message="Hello")
        assert request.stream is True
        assert request.reasoning_effort is None
        assert request.conversation_id is None

    def test_reasoning_effort_valid_values(self):
        """Test valid reasoning effort values."""
        for effort in ["minimal", "medium", "maximal"]:
            request = ChatRequest(message="Hello", reasoning_effort=effort)  # type: ignore[arg-type]
            assert request.reasoning_effort == effort


class TestStreamEventType:
    """Tests for StreamEventType enum."""

    def test_all_expected_types_exist(self):
        """Ensure all expected event types are defined."""
        expected = [
            "orchestrator.message",
            "orchestrator.thought",
            "response.delta",
            "response.completed",
            "reasoning.delta",
            "reasoning.completed",
            "error",
            "done",
        ]

        for event_type in expected:
            # Should not raise
            StreamEventType(event_type)


class TestStreamingEndpointIntegration:
    """Integration tests for the /api/chat endpoint.

    Note: These tests mock the dependencies to avoid needing the full workflow.
    For full integration tests, see the app/test_endpoints.py pattern.
    """

    def test_non_streaming_request_validation(self):
        """Test that ChatRequest with stream=False is valid but should be rejected.

        The actual rejection happens in the endpoint, not in validation.
        This test verifies the request model accepts stream=False.
        """
        request = ChatRequest(message="Hello", stream=False)
        assert request.stream is False
        assert request.message == "Hello"

    def test_streaming_request_validation(self):
        """Test that ChatRequest with stream=True is valid."""
        request = ChatRequest(message="Hello", stream=True)
        assert request.stream is True
        assert request.message == "Hello"

    def test_sessions_endpoint(self):
        """Test GET /api/sessions returns session list."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from agentic_fleet.app.routers import streaming

        test_app = FastAPI()
        test_app.include_router(streaming.router, prefix="/api")

        with patch("agentic_fleet.app.dependencies.get_session_manager") as mock_sm:
            mock_manager = MagicMock()
            mock_manager.list_sessions.return_value = []
            mock_sm.return_value = mock_manager

            client = TestClient(test_app)
            response = client.get("/api/sessions")

            assert response.status_code == status.HTTP_200_OK
            assert isinstance(response.json(), list)

    def test_session_not_found(self):
        """Test GET /api/sessions/{id} with non-existent ID."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from agentic_fleet.app.routers import streaming

        test_app = FastAPI()
        test_app.include_router(streaming.router, prefix="/api")

        with patch("agentic_fleet.app.dependencies.get_session_manager") as mock_sm:
            mock_manager = MagicMock()
            mock_manager.get_session.return_value = None
            mock_sm.return_value = mock_manager

            client = TestClient(test_app)
            response = client.get("/api/sessions/wf-nonexistent")

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestEventMapping:
    """Tests for workflow event to SSE event mapping."""

    def test_orchestrator_message_type(self):
        """Test orchestrator.message event type value."""
        assert StreamEventType.ORCHESTRATOR_MESSAGE.value == "orchestrator.message"

    def test_reasoning_delta_type(self):
        """Test reasoning.delta event type value."""
        assert StreamEventType.REASONING_DELTA.value == "reasoning.delta"

    def test_response_completed_type(self):
        """Test response.completed event type value."""
        assert StreamEventType.RESPONSE_COMPLETED.value == "response.completed"
