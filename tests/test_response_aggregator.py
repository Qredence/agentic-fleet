"""Unit tests for ResponseAggregator service."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any, cast

import pytest

from agentic_fleet.api.responses.service import ResponseAggregator
from agentic_fleet.models.events import WorkflowEvent


async def generate_mock_events(events: list[dict[str, Any]]) -> AsyncGenerator[WorkflowEvent, None]:
    """Helper to generate mock workflow events."""
    for event in events:
        yield cast(WorkflowEvent, event)


@pytest.mark.asyncio
async def test_convert_stream_delta_events() -> None:
    """Test convert_stream properly converts message.delta events."""
    aggregator = ResponseAggregator()

    events = [
        {"type": "message.delta", "data": {"delta": "Hello", "agent_id": "test_agent"}},
        {"type": "message.delta", "data": {"delta": " World", "agent_id": "test_agent"}},
    ]

    stream = aggregator.convert_stream(generate_mock_events(events))
    lines = []
    async for line in stream:
        lines.append(line)

    # Should have delta events and completion
    assert len([line for line in lines if "response.delta" in line]) == 2
    assert any("[DONE]" in line for line in lines)


@pytest.mark.asyncio
async def test_convert_stream_orchestrator_events() -> None:
    """Test convert_stream handles orchestrator.message events."""
    aggregator = ResponseAggregator()

    events = [
        {
            "type": "orchestrator.message",
            "data": {"message": "Planning task", "kind": "plan"},
        }
    ]

    stream = aggregator.convert_stream(generate_mock_events(events))
    lines = []
    async for line in stream:
        lines.append(line)

    # Should have orchestrator event
    assert any("orchestrator.message" in line for line in lines)
    assert any("Planning task" in line for line in lines)
    assert any("[DONE]" in line for line in lines)


@pytest.mark.asyncio
async def test_convert_stream_completion() -> None:
    """Test convert_stream sends response.completed and [DONE]."""
    aggregator = ResponseAggregator()

    events = [
        {"type": "message.delta", "data": {"delta": "Test", "agent_id": "test"}},
        {"type": "message.done", "data": {"result": "Test result"}},
    ]

    stream = aggregator.convert_stream(generate_mock_events(events))
    lines = []
    async for line in stream:
        lines.append(line)

    # Should have completion event
    assert any("response.completed" in line for line in lines)
    assert any("[DONE]" in line for line in lines)
    # [DONE] should be last
    assert lines[-1].strip() == "data: [DONE]"


@pytest.mark.asyncio
async def test_completion_event_emitted_with_zero_deltas() -> None:
    """Completion event should be emitted even when no delta chunks were streamed."""
    aggregator = ResponseAggregator()

    events = [
        {"type": "message.done", "data": {"result": ""}},
    ]

    stream = aggregator.convert_stream(generate_mock_events(events))
    lines = []
    async for line in stream:
        lines.append(line)

    completion_events = [
        json.loads(line.replace("data: ", "")) for line in lines if "response.completed" in line
    ]

    assert len(completion_events) == 1
    assert completion_events[0]["response"]["content"] == ""
    assert any("[DONE]" in line for line in lines)
    assert lines[-1].strip() == "data: [DONE]"
    assert aggregator.get_final_response() == ""


@pytest.mark.asyncio
async def test_message_done_overrides_accumulated_delta() -> None:
    """Result payload from message.done should override accumulated delta text."""
    aggregator = ResponseAggregator()

    events = [
        {"type": "message.delta", "data": {"delta": "Partial", "agent_id": "test"}},
        {"type": "message.done", "data": {"result": "Final content"}},
    ]

    stream = aggregator.convert_stream(generate_mock_events(events))
    async for _ in stream:
        # Drain stream; we only care about aggregator state
        pass

    assert aggregator.get_final_response() == "Final content"


@pytest.mark.asyncio
async def test_convert_stream_error_handling() -> None:
    """Test convert_stream converts error events to SSE format."""
    aggregator = ResponseAggregator()

    events = [
        {"type": "error", "data": {"error": "Test error"}},
    ]

    stream = aggregator.convert_stream(generate_mock_events(events))
    lines = []
    async for line in stream:
        lines.append(line)

    # Should have error event
    assert any("error" in line for line in lines)
    assert any("Test error" in line for line in lines)
    assert any("[DONE]" in line for line in lines)


@pytest.mark.asyncio
async def test_convert_stream_accumulation() -> None:
    """Test convert_stream accumulates content across multiple deltas."""
    aggregator = ResponseAggregator()

    events = [
        {"type": "message.delta", "data": {"delta": "Hello", "agent_id": "test"}},
        {"type": "message.delta", "data": {"delta": " ", "agent_id": "test"}},
        {"type": "message.delta", "data": {"delta": "World", "agent_id": "test"}},
    ]

    stream = aggregator.convert_stream(generate_mock_events(events))
    lines = []
    async for line in stream:
        lines.append(line)

    # Should have accumulated content in completion
    completion_lines = [line for line in lines if "response.completed" in line]
    assert len(completion_lines) > 0
    completion_data = json.loads(completion_lines[0].replace("data: ", ""))
    assert "Hello World" in completion_data["response"]["content"]


@pytest.mark.asyncio
async def test_convert_stream_missing_done_event() -> None:
    """Test convert_stream sends completion even without explicit done event."""
    aggregator = ResponseAggregator()

    events = [
        {"type": "message.delta", "data": {"delta": "Test", "agent_id": "test"}},
        # No message.done event
    ]

    stream = aggregator.convert_stream(generate_mock_events(events))
    lines = []
    async for line in stream:
        lines.append(line)

    # Should still send completion
    assert any("response.completed" in line for line in lines)
    assert any("[DONE]" in line for line in lines)


@pytest.mark.asyncio
async def test_openai_response_completed_updates_final_content() -> None:
    """OpenAI-formatted response.completed events should populate final content."""
    aggregator = ResponseAggregator()

    events = [
        {
            "type": "workflow.complete",
            "openai_type": "response.completed",
            "data": {
                "response": {
                    "role": "assistant",
                    "content": "OpenAI final result",
                }
            },
        }
    ]

    stream = aggregator.convert_stream(generate_mock_events(events))
    lines = []
    async for line in stream:
        lines.append(line)

    assert any("response.completed" in line for line in lines)
    assert aggregator.get_final_response() == "OpenAI final result"
    assert lines[-1].strip() == "data: [DONE]"


def test_get_final_response() -> None:
    """Test get_final_response returns accumulated content."""
    aggregator = ResponseAggregator()
    aggregator._accumulated_content = "Test content"

    assert aggregator.get_final_response() == "Test content"


def test_reset() -> None:
    """Test reset clears accumulated state."""
    aggregator = ResponseAggregator()
    aggregator._accumulated_content = "Test content"
    aggregator._agent_id = "test_agent"

    aggregator.reset()

    assert aggregator._accumulated_content == ""
    assert aggregator._agent_id is None


@pytest.mark.asyncio
async def test_sse_format_compliance() -> None:
    """Test all events follow SSE format: data: {json}\n\n."""
    aggregator = ResponseAggregator()

    events = [
        {"type": "message.delta", "data": {"delta": "Test", "agent_id": "test"}},
    ]

    stream = aggregator.convert_stream(generate_mock_events(events))
    lines = []
    async for line in stream:
        lines.append(line)

    # All lines should start with "data: " and end with "\n\n"
    for line in lines:
        if line.strip() and line.strip() != "data: [DONE]":
            assert line.startswith("data: ")
            assert line.endswith("\n\n")
            # Should be valid JSON after "data: "
            json_str = line.replace("data: ", "").strip()
            if json_str != "[DONE]":
                json.loads(json_str)  # Should not raise


@pytest.mark.asyncio
async def test_exception_handling() -> None:
    """Test exception handling in convert_stream."""
    aggregator = ResponseAggregator()

    async def failing_events() -> AsyncGenerator[WorkflowEvent, None]:
        yield {"type": "message.delta", "data": {"delta": "Test"}}
        raise RuntimeError("Test error")

    stream = aggregator.convert_stream(failing_events())
    lines = []
    async for line in stream:
        lines.append(line)

    # Should have error event
    assert any("error" in line for line in lines)
    assert any("[DONE]" in line for line in lines)
