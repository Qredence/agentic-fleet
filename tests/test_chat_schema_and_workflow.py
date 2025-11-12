"""Tests covering chat schemas and workflow stubs.

These tests replace the legacy memory system suite. They validate key pieces of the
REST-first architecture:

- Pydantic validation for chat request/response models
- Behaviour of the stub workflow used by the chat route
- WorkflowService for separating concerns
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from pydantic import ValidationError

import agentic_fleet.api.chat.service as service_module
from agentic_fleet.api.chat.schemas import ChatMessagePayload, ChatRequest, ChatResponse
from agentic_fleet.api.exceptions import WorkflowExecutionError
from agentic_fleet.api.workflows.service import (
    StubMagenticFleetWorkflow,
    WorkflowEvent,
    create_magentic_fleet_workflow,
)


class TestChatSchemas:
    """Validation tests for chat request/response schemas."""

    def test_chat_request_requires_message(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest.model_validate({"conversation_id": "abc"})

    def test_chat_request_requires_conversation(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest.model_validate({"message": "Hello"})

    def test_chat_response_shape(self) -> None:
        payload = ChatResponse(
            conversation_id="conv-1",
            message="Hi",
            messages=[
                ChatMessagePayload(
                    id="msg-1",
                    role="user",
                    content="Hi",
                    created_at=1700000000,
                ),
                ChatMessagePayload(
                    id="msg-2",
                    role="assistant",
                    content="Hello!",
                    created_at=1700000001,
                ),
            ],
        )

        assert payload.conversation_id == "conv-1"
        assert payload.messages[0].role == "user"
        assert payload.messages[1].role == "assistant"


@pytest.mark.asyncio
async def test_stub_workflow_yields_delta_then_done() -> None:
    workflow = create_magentic_fleet_workflow()
    # Legacy synchronous factory returns instance directly (no await needed)
    assert isinstance(workflow, StubMagenticFleetWorkflow)

    events: list[WorkflowEvent] = []
    stream = workflow.run("Summarise AgenticFleet")
    assert isinstance(stream, AsyncGenerator)

    async for event in stream:
        events.append(event)

    # Legacy stub emits only delta + done (no agent completion event)
    assert [event.get("type") for event in events] == ["message.delta", "message.done"]
    assert "delta" in events[0].get("data", {})


class TestWorkflowService:
    """Tests for WorkflowService class."""

    @pytest.mark.asyncio
    async def test_execute_workflow_returns_aggregated_result(self) -> None:
        service = service_module.WorkflowService()
        # Inject stub workflow into cache to test execute_workflow with known behavior
        stub_workflow = create_magentic_fleet_workflow()
        service._workflow_cache["magentic_fleet"] = stub_workflow

        result = await service.execute_workflow("Test message")
        # Stub workflow returns the full message
        assert result == "Test message"

    @pytest.mark.asyncio
    async def test_process_workflow_events_aggregates_deltas(self) -> None:
        service = service_module.WorkflowService()

        async def mock_events() -> AsyncGenerator[WorkflowEvent, None]:
            yield {"type": "message.delta", "data": {"delta": "Hello "}}
            yield {"type": "message.delta", "data": {"delta": "World"}}
            yield {"type": "message.done", "data": {}}

        result = await service.process_workflow_events(mock_events())
        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_process_workflow_events_stops_at_done(self) -> None:
        service = service_module.WorkflowService()

        async def mock_events() -> AsyncGenerator[WorkflowEvent, None]:
            yield {"type": "message.delta", "data": {"delta": "Keep"}}
            yield {"type": "message.done", "data": {}}
            yield {"type": "message.delta", "data": {"delta": "Skip"}}

        result = await service.process_workflow_events(mock_events())
        assert result == "Keep"

    @pytest.mark.asyncio
    async def test_execute_workflow_raises_domain_exception_on_error(self) -> None:
        service = service_module.WorkflowService()

        # Create a mock workflow that raises an exception
        class FailingWorkflow:
            async def run(self, message: str) -> AsyncGenerator[WorkflowEvent, None]:
                raise RuntimeError("Workflow failed")
                yield  # pragma: no cover

        # Directly inject failing workflow into cache (bypassing factory logic)
        service._workflow_cache["magentic_fleet"] = FailingWorkflow()  # type: ignore[arg-type]

        try:
            with pytest.raises(WorkflowExecutionError) as exc_info:
                await service.execute_workflow("Test")
            # Domain exception exposes message via str(exc)
            assert "An error occurred while processing" in str(exc_info.value)
        finally:
            service._workflow_cache.clear()  # Clean up for subsequent tests

    def test_get_workflow_service_returns_singleton(self) -> None:
        service1 = service_module.get_workflow_service()
        service2 = service_module.get_workflow_service()
        assert service1 is service2
