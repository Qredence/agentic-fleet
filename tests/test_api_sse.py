from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from httpx_sse import aconnect_sse

from agentic_fleet.api.app import create_app


@pytest.mark.asyncio
async def test_chat_non_streaming() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_resp = await ac.post("/v1/conversations")
        conversation_id = create_resp.json()["id"]

        resp = await ac.post(
            "/v1/chat",
            json={"conversation_id": conversation_id, "message": "hello world"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert isinstance(data["message"], str)
        assert len(data["messages"]) == 2


@pytest.mark.asyncio
async def test_chat_streaming() -> None:
    """Test SSE streaming endpoint for chat."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create a conversation
        create_resp = await ac.post("/v1/conversations")
        conversation_id = create_resp.json()["id"]

        # Test streaming endpoint
        events_received = []
        async with aconnect_sse(
            ac,
            "POST",
            "/v1/chat/stream",
            json={"conversation_id": conversation_id, "message": "test streaming"},
        ) as event_source:
            async for sse in event_source.aiter_sse():
                events_received.append(sse)
                if sse.event == "message":
                    import json
                    data = json.loads(sse.data)
                    if data.get("type") == "done":
                        break

        # Verify we received events
        assert len(events_received) > 0
        # Check that we have at least one done event
        done_events = [e for e in events_received if "done" in e.data]
        assert len(done_events) > 0
