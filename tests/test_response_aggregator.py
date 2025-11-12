"""Unit tests for ResponseAggregator streaming behaviour."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

import pytest

from agentic_fleet.api.responses.service import ResponseAggregator
from agentic_fleet.models.events import WorkflowEvent


async def _iter_events(events: list[WorkflowEvent]) -> AsyncGenerator[WorkflowEvent, None]:
    for event in events:
        yield event
        await asyncio.sleep(0)


def _parse_sse_chunks(chunks: list[str]) -> list[dict[str, object]]:
    parsed: list[dict[str, object]] = []
    for chunk in chunks:
        if not chunk.startswith("data: "):
            continue
        payload = chunk[6:].strip()
        if not payload:
            continue
        if payload == "[DONE]":
            parsed.append({"type": "done"})
            continue
        parsed.append(json.loads(payload))
    return parsed


@pytest.mark.asyncio
async def test_response_aggregator_streams_reasoning_deltas() -> None:
    """Aggregator should relay incremental reasoning and aggregate on completion."""

    aggregator = ResponseAggregator()
    events: list[WorkflowEvent] = [
        {
            "type": "reasoning.delta",
            "data": {"delta": "Step 1. ", "agent_id": "planner"},
        },
        {
            "type": "reasoning.delta",
            "data": {"delta": "Step 2.", "agent_id": "planner"},
        },
        {
            "type": "message.delta",
            "data": {"delta": "Answer", "agent_id": "planner"},
        },
        {
            "type": "message.done",
            "data": {"result": "Answer", "agent_id": "planner"},
        },
    ]

    chunks: list[str] = []
    async for chunk in aggregator.convert_stream(_iter_events(events)):
        chunks.append(chunk)

    parsed_events = _parse_sse_chunks(chunks)

    reasoning_delta_events = [
        event for event in parsed_events if event.get("type") == "reasoning.delta"
    ]
    assert [event.get("reasoning") for event in reasoning_delta_events] == [
        "Step 1. ",
        "Step 2.",
    ]

    reasoning_completed = next(
        event for event in parsed_events if event.get("type") == "reasoning.completed"
    )
    assert reasoning_completed.get("reasoning") == "Step 1. Step 2."
    assert reasoning_completed.get("agent_id") == "planner"

    response_completed = next(
        event for event in parsed_events if event.get("type") == "response.completed"
    )
    response_payload = response_completed.get("response")
    assert isinstance(response_payload, dict)
    assert response_payload.get("content") == "Answer"

    assert parsed_events[-1]["type"] == "done"
