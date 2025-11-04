"""Tests for backward compatibility with existing endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from agentic_fleet.api.app import create_app


@pytest.mark.asyncio
async def test_chat_endpoint() -> None:
    """Test /v1/chat endpoint - verify existing chat endpoint still works."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create conversation first
        create_resp = await client.post("/v1/conversations")
        conversation_id = create_resp.json()["id"]

        # Test chat endpoint
        resp = await client.post(
            "/v1/chat",
            json={"conversation_id": conversation_id, "message": "hello", "stream": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "messages" in data


@pytest.mark.asyncio
async def test_conversations_endpoint() -> None:
    """Test /v1/conversations endpoint - verify conversation management unchanged."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create conversation
        create_resp = await client.post("/v1/conversations")
        assert create_resp.status_code == 201  # POST creates returns 201
        conversation_id = create_resp.json()["id"]
        assert conversation_id

        # Get conversation
        get_resp = await client.get(f"/v1/conversations/{conversation_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == conversation_id


@pytest.mark.asyncio
async def test_workflows_endpoint() -> None:
    """Test /v1/workflows endpoint - verify workflow discovery endpoint unchanged."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/workflows")
        assert resp.status_code == 200
        data = resp.json()
        assert "workflows" in data
        assert isinstance(data["workflows"], list)


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    """Test /v1/system/health endpoint - verify health check unchanged."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/system/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


@pytest.mark.asyncio
async def test_existing_sse_format() -> None:
    """Test existing SSE format - verify existing chat SSE format still supported."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create conversation
        create_resp = await client.post("/v1/conversations")
        conversation_id = create_resp.json()["id"]

        # Test streaming chat
        resp = await client.post(
            "/v1/chat",
            json={"conversation_id": conversation_id, "message": "test", "stream": True},
            headers={"Accept": "text/event-stream"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        # Read stream
        content = b""
        async for chunk in resp.aiter_bytes():
            content += chunk
            if b"[DONE]" in content:
                break

        assert b"[DONE]" in content


@pytest.mark.asyncio
async def test_conversation_persistence() -> None:
    """Test conversation persistence - verify conversations still persist correctly."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create conversation
        create_resp = await client.post("/v1/conversations")
        conversation_id = create_resp.json()["id"]

        # Add message
        chat_resp = await client.post(
            "/v1/chat",
            json={"conversation_id": conversation_id, "message": "test message", "stream": False},
        )
        assert chat_resp.status_code == 200

        # Get conversation - should have messages
        get_resp = await client.get(f"/v1/conversations/{conversation_id}")
        assert get_resp.status_code == 200
        conversation = get_resp.json()
        assert "messages" in conversation
        assert len(conversation["messages"]) >= 2  # User message + assistant response
