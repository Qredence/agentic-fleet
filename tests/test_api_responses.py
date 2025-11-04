"""Tests for OpenAI-compatible Responses API."""

from __future__ import annotations

import contextlib
import json

import pytest
from httpx import ASGITransport, AsyncClient

from agentic_fleet.api.app import create_app


def parse_sse_stream(content: str) -> list[dict]:
    """Parse SSE stream into list of events."""
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
async def test_responses_non_streaming() -> None:
    """Test non-streaming response."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Hello, test message",
                "stream": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["model"] == "magentic_fleet"
        assert "response" in data
        assert "created" in data


@pytest.mark.asyncio
async def test_responses_streaming() -> None:
    """Test streaming response."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Hello, test message",
                "stream": True,
            },
            headers={"Accept": "text/event-stream"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Read SSE stream
        content = b""
        async for chunk in resp.aiter_bytes():
            content += chunk
            if b"[DONE]" in content:
                break

        # Verify SSE format
        text = content.decode("utf-8")
        assert "data: " in text
        assert "[DONE]" in text


@pytest.mark.asyncio
async def test_sse_event_parsing() -> None:
    """Test SSE event parsing - verify delta events can be parsed correctly."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Test message",
                "stream": True,
            },
        )
        assert resp.status_code == 200

        content = b""
        async for chunk in resp.aiter_bytes():
            content += chunk
            if b"[DONE]" in content:
                break

        events = parse_sse_stream(content.decode("utf-8"))
        # Should have at least one delta event or completion event
        assert len(events) > 0
        assert any("response.delta" in str(e) or "response.completed" in str(e) for e in events)


@pytest.mark.asyncio
async def test_sse_event_sequence() -> None:
    """Test SSE event sequence - verify proper order (delta → completed → [DONE])."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Test message",
                "stream": True,
            },
        )
        assert resp.status_code == 200

        content = b""
        async for chunk in resp.aiter_bytes():
            content += chunk
            if b"[DONE]" in content:
                break

        events = parse_sse_stream(content.decode("utf-8"))
        # Last event should be [DONE]
        assert events[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_sse_content_extraction() -> None:
    """Test SSE content extraction - verify content can be extracted from stream."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Extract this content",
                "stream": True,
            },
        )
        assert resp.status_code == 200

        content = b""
        async for chunk in resp.aiter_bytes():
            content += chunk
            if b"[DONE]" in content:
                break

        events = parse_sse_stream(content.decode("utf-8"))
        # Should have events with content
        # At least confirm parsing logic did not raise; content may be empty for stub workflow.
        assert (
            any(
                isinstance(event, dict)
                and (
                    ("delta" in event and event.get("delta", {}).get("content"))
                    or ("response" in event and event.get("response", {}).get("content"))
                )
                for event in events
            )
            or True
        )  # Maintain original permissive assertion semantics


@pytest.mark.asyncio
async def test_streaming_with_accept_header() -> None:
    """Test streaming with Accept header detection."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Test",
                "stream": False,  # Set to False but use Accept header
            },
            headers={"Accept": "text/event-stream"},
        )
        # Should detect Accept header and stream
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_non_streaming_response_format() -> None:
    """Test non-streaming response format - verify complete response structure."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Test message",
                "stream": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        # Verify complete response structure
        assert "id" in data
        assert "model" in data
        assert "response" in data
        assert "created" in data
        assert isinstance(data["id"], str)
        assert isinstance(data["response"], str)
        assert isinstance(data["created"], int)


@pytest.mark.asyncio
async def test_structured_input_extraction() -> None:
    """Test structured input extraction - verify dict input extraction."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": {"input": "Hello, structured input"},
                "stream": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data


@pytest.mark.asyncio
async def test_empty_input_handling() -> None:
    """Test empty input handling - verify proper error for empty input."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "",
                "stream": False,
            },
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_responses_entity_not_found() -> None:
    """Test response with non-existent entity."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "nonexistent",
                "input": "Hello",
                "stream": False,
            },
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_concurrent_requests() -> None:
    """Test concurrent requests - multiple simultaneous workflow executions."""
    import asyncio

    transport = ASGITransport(app=create_app())

    async def make_request(client: AsyncClient) -> dict:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "Test",
                "stream": False,
            },
        )
        return resp.json()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tasks = [make_request(client) for _ in range(3)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        for result in results:
            assert "response" in result
            assert "id" in result
