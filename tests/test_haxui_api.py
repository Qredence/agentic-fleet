import pytest
from httpx import ASGITransport, AsyncClient

from agenticfleet.haxui import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_health_endpoint(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert "version" in payload


@pytest.mark.asyncio
async def test_entity_listing(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/entities")
        assert response.status_code == 200
        payload = response.json()
        assert "entities" in payload
        assert any(entity["type"] == "agent" for entity in payload["entities"])
        assert any(entity["type"] == "workflow" for entity in payload["entities"])


@pytest.mark.asyncio
async def test_streaming_response(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "model": "magentic_fleet",
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Say hello"}],
                }
            ],
        }
        response = await client.post(
            "/v1/responses",
            json=payload,
            headers={"accept": "text/event-stream"},
            timeout=30.0,
        )
        assert response.status_code == 200

        chunks = []
        async for chunk in response.aiter_text():
            chunks.append(chunk)

        body = "".join(chunks)
        assert "[DONE]" in body
        assert "response.completed" in body
        assert '"conversation_id"' in body
