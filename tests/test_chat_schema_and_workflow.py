"""Tests covering chat schemas and workflow stubs.

These tests replace the legacy memory system suite. They validate key pieces of the
REST-first architecture:

- Pydantic validation for chat request/response models
- Behaviour of the stub workflow used by the chat route
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from pydantic import ValidationError

from agentic_fleet.api.chat.schemas import ChatMessagePayload, ChatRequest, ChatResponse
from agentic_fleet.api.workflows.service import (
    StubMagenticFleetWorkflow,
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
    assert isinstance(workflow, StubMagenticFleetWorkflow)

    events: list[dict] = []
    stream = workflow.run("Summarise AgenticFleet")
    assert isinstance(stream, AsyncGenerator)

    async for event in stream:
        events.append(event)

    assert [event["type"] for event in events] == ["message.delta", "message.done"]
    assert "delta" in events[0]["data"]
