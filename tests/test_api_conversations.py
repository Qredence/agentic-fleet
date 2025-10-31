from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from agentic_fleet.api.app import create_app


@pytest.mark.asyncio
async def test_conversations_crud() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create
        resp = await ac.post("/v1/conversations")
        assert resp.status_code == 201
        created = resp.json()
        cid = created["id"]
        assert created["messages"] == []
        assert isinstance(created["created_at"], int)

        # List
        resp = await ac.get("/v1/conversations")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(item["id"] == cid for item in items)

        # Get
        resp = await ac.get(f"/v1/conversations/{cid}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == cid
        assert "messages" in body
        assert isinstance(body["messages"], list)
