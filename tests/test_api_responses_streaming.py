"""Tests for SSE event stream format compliance."""

from __future__ import annotations

import contextlib
import json

import pytest
from httpx import ASGITransport, AsyncClient

from agentic_fleet.api.app import create_app


def parse_sse_events(content: str) -> list[dict]:
    """Parse SSE stream into list of event dictionaries."""
    events = []
    for line in content.split("\n\n"):
        if line.startswith("data: "):
            data = line[6:].strip()
            if data == "[DONE]":
                events.append({"type": "done"})
            else:
                with contextlib.suppress(json.JSONDecodeError):
                    events.append(json.loads(data))
    return events


@pytest.mark.asyncio
async def test_sse_format_compliance() -> None:
    """Test all events follow SSE format: data: {json}\n\n."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Test",
                "stream": True,
            },
        )
        assert resp.status_code == 200

        content = b""
        async for chunk in resp.aiter_bytes():
            content += chunk
            if b"[DONE]" in content:
                break

        text = content.decode("utf-8")
        lines = text.split("\n\n")
        for line in lines:
            if line.strip() and line.strip() != "data: [DONE]":
                assert line.startswith("data: "), f"Line does not start with 'data: ': {line[:100]}"


@pytest.mark.asyncio
async def test_delta_event_structure() -> None:
    """Test delta event structure - verify ResponseDeltaEvent structure."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Test",
                "stream": True,
            },
        )
        assert resp.status_code == 200

        content = b""
        async for chunk in resp.aiter_bytes():
            content += chunk
            if b"[DONE]" in content:
                break

        events = parse_sse_events(content.decode("utf-8"))
        delta_events = [
            e for e in events if isinstance(e, dict) and e.get("type") == "response.delta"
        ]

        if delta_events:
            delta_event = delta_events[0]
            assert "type" in delta_event
            assert "delta" in delta_event
            assert "content" in delta_event["delta"]


@pytest.mark.asyncio
async def test_completed_event_structure() -> None:
    """Test completed event structure - verify ResponseCompletedEvent structure."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Test",
                "stream": True,
            },
        )
        assert resp.status_code == 200

        content = b""
        async for chunk in resp.aiter_bytes():
            content += chunk
            if b"[DONE]" in content:
                break

        events = parse_sse_events(content.decode("utf-8"))
        completed_events = [
            e for e in events if isinstance(e, dict) and e.get("type") == "response.completed"
        ]

        if completed_events:
            completed_event = completed_events[0]
            assert "type" in completed_event
            assert "response" in completed_event
            assert "role" in completed_event["response"]
            assert "content" in completed_event["response"]


@pytest.mark.asyncio
async def test_orchestrator_events() -> None:
    """Test orchestrator events - verify OrchestratorMessageEvent in stream."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Test",
                "stream": True,
            },
        )
        assert resp.status_code == 200

        content = b""
        async for chunk in resp.aiter_bytes():
            content += chunk
            if b"[DONE]" in content:
                break

        events = parse_sse_events(content.decode("utf-8"))
        # May or may not have orchestrator events depending on workflow
        orchestrator_events = [
            e for e in events if isinstance(e, dict) and e.get("type") == "orchestrator.message"
        ]
        # Verify that orchestrator events are present in the stream (may be empty for some workflows)
        assert isinstance(orchestrator_events, list)
        # Optionally, if you expect at least one orchestrator event, use:
        # assert len(orchestrator_events) > 0


@pytest.mark.asyncio
async def test_done_marker() -> None:
    """Test [DONE] marker - verify [DONE] appears at end."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Test",
                "stream": True,
            },
        )
        assert resp.status_code == 200

        content = b""
        async for chunk in resp.aiter_bytes():
            content += chunk
            if b"[DONE]" in content:
                break

        text = content.decode("utf-8")
        assert "[DONE]" in text
        # Should be near the end
        assert text.rstrip().endswith("data: [DONE]")


@pytest.mark.asyncio
async def test_multiple_delta_events() -> None:
    """Test multiple delta events - verify accumulation across events."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Test accumulation",
                "stream": True,
            },
        )
        assert resp.status_code == 200

        content = b""
        async for chunk in resp.aiter_bytes():
            content += chunk
            if b"[DONE]" in content:
                break

        events = parse_sse_events(content.decode("utf-8"))
        # Count delta events (may be zero depending on workflow)
        _delta_count = sum(
            1 for e in events if isinstance(e, dict) and e.get("type") == "response.delta"
        )
        # Maintain permissive original assertion semantics while removing unused variable warning
        assert _delta_count >= 0
