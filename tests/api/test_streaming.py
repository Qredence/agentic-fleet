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

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from agentic_fleet.main import app
from agentic_fleet.models import (
    ChatRequest,
    StreamEvent,
    StreamEventType,
    WorkflowResumeRequest,
    WorkflowStatus,
)
from agentic_fleet.services.conversation import WorkflowSessionManager


@pytest.fixture
def client():
    """Create a test client."""
    with patch(
        "agentic_fleet.api.lifespan.create_supervisor_workflow", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = MagicMock()
        with TestClient(app) as client:
            yield client


@pytest.fixture
def session_manager():
    """Create a fresh session manager with default concurrency limit (2)."""
    return WorkflowSessionManager(max_concurrent=2)


@pytest.fixture
def session_manager_concurrent():
    """Create a session manager with higher concurrency limit for concurrency tests."""
    return WorkflowSessionManager(max_concurrent=10)


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


@pytest.mark.asyncio
class TestWorkflowSessionManager:
    """Tests for session manager functionality."""

    async def test_create_session(self, session_manager):
        """Test session creation."""
        session = await session_manager.create_session(
            task="Test task",
            reasoning_effort="medium",
        )

        assert session.workflow_id.startswith("wf-")
        assert session.task == "Test task"
        assert session.status == WorkflowStatus.CREATED
        assert session.reasoning_effort == "medium"
        assert isinstance(session.created_at, datetime)

    async def test_get_session(self, session_manager):
        """Test retrieving a session."""
        created = await session_manager.create_session(task="Test")
        retrieved = await session_manager.get_session(created.workflow_id)

        assert retrieved is not None
        assert retrieved.workflow_id == created.workflow_id

    async def test_get_session_not_found(self, session_manager):
        """Test retrieving non-existent session."""
        result = await session_manager.get_session("wf-nonexistent")
        assert result is None

    async def test_update_status(self, session_manager):
        """Test status update."""
        session = await session_manager.create_session(task="Test")
        now = datetime.now()

        await session_manager.update_status(
            session.workflow_id,
            WorkflowStatus.RUNNING,
            started_at=now,
        )

        updated = await session_manager.get_session(session.workflow_id)
        assert updated is not None
        assert updated.status == WorkflowStatus.RUNNING
        assert updated.started_at == now

    async def test_count_active(self, session_manager):
        """Test counting active workflows."""
        assert await session_manager.count_active() == 0

        s1 = await session_manager.create_session(task="Task 1")
        assert await session_manager.count_active() == 1

        await session_manager.create_session(task="Task 2")  # s2 not needed
        assert await session_manager.count_active() == 2

        await session_manager.update_status(s1.workflow_id, WorkflowStatus.COMPLETED)
        assert await session_manager.count_active() == 1

    async def test_concurrent_limit_enforced(self, session_manager):
        """Test that concurrent limit raises 429."""
        from fastapi import HTTPException

        # Create max sessions
        await session_manager.create_session(task="Task 1")
        await session_manager.create_session(task="Task 2")

        # Third should fail
        with pytest.raises(HTTPException, match="Maximum concurrent"):
            await session_manager.create_session(task="Task 3")

    async def test_list_sessions(self, session_manager):
        """Test listing all sessions."""
        await session_manager.create_session(task="Task 1")
        await session_manager.create_session(task="Task 2")

        sessions = await session_manager.list_sessions()
        assert len(sessions) == 2

    async def test_cleanup_completed(self, session_manager):
        """Test cleanup of old completed sessions."""
        s1 = await session_manager.create_session(task="Task 1")
        await session_manager.update_status(s1.workflow_id, WorkflowStatus.COMPLETED)

        # Mock old timestamp
        session = await session_manager.get_session(s1.workflow_id)
        if session:
            session.created_at = datetime(2020, 1, 1)  # Very old

        cleaned = await session_manager.cleanup_completed(max_age_seconds=60)
        assert cleaned == 1
        assert await session_manager.get_session(s1.workflow_id) is None

    async def test_concurrent_creation_and_updates(self, session_manager_concurrent):
        """Ensure concurrent operations maintain consistent counts and state."""

        async def _create(task: str):
            return await session_manager_concurrent.create_session(task=task)

        sessions = await asyncio.gather(
            _create("Task A"),
            _create("Task B"),
        )

        assert len(sessions) == 2
        assert await session_manager_concurrent.count_active() == 2

        await asyncio.gather(
            *(
                session_manager_concurrent.update_status(
                    session.workflow_id, WorkflowStatus.RUNNING
                )
                for session in sessions
            )
        )

        stored_sessions = await session_manager_concurrent.list_sessions()
        assert all(s.status == WorkflowStatus.RUNNING for s in stored_sessions)
        assert await session_manager_concurrent.count_active() == 2

    async def test_concurrent_status_progression(self, session_manager):
        """Concurrent status changes should settle on the latest update."""
        session = await session_manager.create_session(task="Progress task")

        start_time = datetime.now()
        end_time = datetime.now()

        await asyncio.gather(
            session_manager.update_status(
                session.workflow_id, WorkflowStatus.RUNNING, started_at=start_time
            ),
            session_manager.update_status(
                session.workflow_id, WorkflowStatus.COMPLETED, completed_at=end_time
            ),
        )

        stored = await session_manager.get_session(session.workflow_id)
        assert stored is not None
        assert stored.status == WorkflowStatus.COMPLETED
        assert stored.completed_at == end_time
        # started_at may or may not be set depending on race outcome
        # If we need deterministic behavior, use sequential updates instead


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
        assert request.enable_checkpointing is False
        assert request.checkpoint_id is None

    def test_checkpoint_id_optional(self):
        """ChatRequest should accept an optional checkpoint_id."""
        request = ChatRequest(message="Hello", checkpoint_id="ckpt-123")
        assert request.checkpoint_id == "ckpt-123"

    def test_enable_checkpointing_optional(self):
        """ChatRequest should accept enable_checkpointing for new runs."""
        request = ChatRequest(message="Hello", enable_checkpointing=True)
        assert request.enable_checkpointing is True

    def test_reasoning_effort_valid_values(self):
        """Test valid reasoning effort values."""
        for effort in ["minimal", "medium", "maximal"]:
            request = ChatRequest(message="Hello", reasoning_effort=effort)  # type: ignore[arg-type]
            assert request.reasoning_effort == effort


class TestWorkflowResumeRequest:
    """Tests for workflow.resume WebSocket message validation."""

    def test_valid_resume_request(self):
        req = WorkflowResumeRequest(
            type="workflow.resume",
            conversation_id="conv-1",
            checkpoint_id="ckpt-123",
            stream=True,
        )
        assert req.type == "workflow.resume"
        assert req.conversation_id == "conv-1"
        assert req.checkpoint_id == "ckpt-123"

    def test_resume_requires_checkpoint_id(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            WorkflowResumeRequest(type="workflow.resume")  # type: ignore[call-arg]


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
        """Test GET /api/v1/sessions returns session list."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from agentic_fleet.api.deps import get_session_manager
        from agentic_fleet.api.routes import sessions

        test_app = FastAPI()
        test_app.include_router(sessions.router, prefix="/api/v1")

        mock_manager = AsyncMock()
        mock_manager.list_sessions.return_value = []
        test_app.dependency_overrides[get_session_manager] = lambda: mock_manager

        with TestClient(test_app) as client:
            response = client.get("/api/v1/sessions")

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_session_not_found(self):
        """Test GET /api/v1/sessions/{id} with non-existent ID."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from agentic_fleet.api.deps import get_session_manager
        from agentic_fleet.api.routes import sessions

        test_app = FastAPI()
        test_app.include_router(sessions.router, prefix="/api/v1")

        mock_manager = AsyncMock()
        mock_manager.get_session.return_value = None
        test_app.dependency_overrides[get_session_manager] = lambda: mock_manager

        with TestClient(test_app) as client:
            response = client.get("/api/v1/sessions/wf-nonexistent")

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
