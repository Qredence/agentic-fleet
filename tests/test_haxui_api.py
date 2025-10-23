from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from agenticfleet.haxui import create_app


@pytest.fixture
def app() -> Any:
    return create_app()


@pytest.mark.asyncio
async def test_health_endpoint(app: Any) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert "version" in payload


@pytest.mark.asyncio
async def test_entity_listing(app: Any) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/entities")
        assert response.status_code == 200
        payload = response.json()
        assert "entities" in payload
        assert any(entity["type"] == "agent" for entity in payload["entities"])
        assert any(entity["type"] == "workflow" for entity in payload["entities"])


@pytest.mark.asyncio
async def test_streaming_response(app: Any) -> None:
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
        assert "queue_metrics" in body

        convo_response = await client.get("/v1/conversations")
        assert convo_response.status_code == 200
    convo_payload = convo_response.json()
    assert convo_payload["data"], "Conversation store did not persist records"


@pytest.mark.asyncio
async def test_approval_listing_and_response(app: Any) -> None:
    handler = app.state.approval_handler
    await handler.initialise()

    request_id = "req_test_1"
    await handler._store.add_request(
        {
            "request_id": request_id,
            "operation_type": "code_execution",
            "agent_name": "coder",
            "operation": "Execute test code",
            "details": {"language": "python"},
            "code": "print('hello')",
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "pending",
        }
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/approvals")
        assert response.status_code == 200
        payload = response.json()
        assert any(item["request_id"] == request_id for item in payload["data"])

        submit = await client.post(
            f"/v1/approvals/{request_id}",
            json={"decision": "approved", "reason": "looks good"},
        )
        assert submit.status_code == 204

        cleared = await client.get("/v1/approvals")
        assert cleared.status_code == 200
        after_payload = cleared.json()
        assert not any(item["request_id"] == request_id for item in after_payload["data"])
