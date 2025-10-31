from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

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
