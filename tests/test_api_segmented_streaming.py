"""Tests for segmented streaming (agent-level and reasoning events).

Ensures the SSE stream carries per-agent completion events and that the
conversation store persists segmented agent messages alongside the legacy
aggregated assistant message when using the stub workflow.
"""

from __future__ import annotations

import contextlib
import json

import pytest
from httpx import ASGITransport, AsyncClient

from agentic_fleet.api.app import create_app


def parse_sse(content: str) -> list[dict]:
    events: list[dict] = []
    for block in content.split("\n\n"):
        if block.startswith("data: "):
            data = block[6:].strip()
            if data == "[DONE]":
                events.append({"type": "done"})
            else:
                with contextlib.suppress(json.JSONDecodeError):
                    events.append(json.loads(data))
    return events


@pytest.mark.asyncio
async def test_segmented_agent_events_and_conversation_persistence() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a new conversation to stream into
        resp = await client.post("/v1/conversations")
        assert resp.status_code == 201
        conversation_id = resp.json()["id"]

        # Perform streaming chat request (stub workflow emits agent + done events)
        stream_resp = await client.get(
            "/v1/chat/stream",
            params={
                "message": "Hello segmented streaming test",
                "conversation_id": conversation_id,
            },
        )
        assert stream_resp.status_code == 200

        raw = b""
        async for chunk in stream_resp.aiter_bytes():
            raw += chunk
            if b"[DONE]" in raw:
                break

        text = raw.decode("utf-8")
        events = parse_sse(text)

        # Verify agent completion event exists (added in stub for determinism)
        agent_complete = [e for e in events if e.get("type") == "agent.message.complete"]
        assert agent_complete, "Expected at least one agent.message.complete event in stream"
        assert agent_complete[0].get("agent_id") == "stub-agent"
        assert isinstance(agent_complete[0].get("content"), str)

        # Verify optional agent.delta events (present because stub delta includes agent_id)
        agent_deltas = [e for e in events if e.get("type") == "agent.delta"]
        assert agent_deltas, "Expected agent.delta events when STREAM_AGENT_DELTAS enabled"
        assert agent_deltas[0].get("agent_id") == "stub-agent"

        # Conversation store should now have: user message + segmented agent message + final aggregated assistant
        conv_resp = await client.get(f"/v1/conversations/{conversation_id}")
        assert conv_resp.status_code == 200
        conv_body = conv_resp.json()
        messages = conv_body["messages"]
        roles = [m["role"] for m in messages]
        assert (
            roles.count("assistant") >= 2
        ), "Expected at least two assistant messages (segmented + final)"

        segmented = [
            m
            for m in messages
            if m["role"] == "assistant" and m["content"].startswith("[stub-agent]")
        ]
        assert (
            segmented
        ), "Segmented agent message with [stub-agent] prefix not found in conversation store"
        final = [
            m
            for m in messages
            if m["role"] == "assistant" and not m["content"].startswith("[stub-agent]")
        ]
        assert final, "Final aggregated assistant message not found"

        # Ensure done marker event present
        assert any(e.get("type") == "done" for e in events), "[DONE] marker missing from stream"
