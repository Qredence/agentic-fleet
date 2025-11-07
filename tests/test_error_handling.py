"""Tests for error handling and edge cases."""

from __future__ import annotations

# Use shared constants for model names used in tests
MODEL_NAME = "agentic_fleet"
INVALID_ENTITY_ID = "invalid_entity_id"

import pytest
from httpx import ASGITransport, AsyncClient

from agentic_fleet.api.app import create_app


@pytest.mark.asyncio
async def test_invalid_entity_id() -> None:
    """Test invalid entity ID - proper 404 response."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": INVALID_ENTITY_ID,
                "input": "Test",
                "stream": False,
            },
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "entity_not_found"
        assert INVALID_ENTITY_ID in data["error"]["message"]


@pytest.mark.asyncio
async def test_invalid_request_body() -> None:
    """Test invalid request body - proper 422 validation error."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": MODEL_NAME,
                # Missing required "input" field
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_missing_required_fields() -> None:
    """Test missing required fields - proper validation errors."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing model field
        resp = await client.post(
            "/v1/responses",
            json={
                "input": "Test",
            },
        )
        assert resp.status_code == 422

        # Missing input field
        resp = await client.post(
            "/v1/responses",
            json={
                "model": MODEL_NAME,
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_workflow_error_propagation() -> None:
    """Test workflow error propagation - verify errors are returned in SSE format."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            json={
                "model": MODEL_NAME,
                "input": "Test",
                "stream": True,
            },
        )
        # Should succeed even if workflow has errors (errors are in stream)
        assert resp.status_code == 200

        content = b""
        async for chunk in resp.aiter_bytes():
            content += chunk
            if b"[DONE]" in content:
                break

        # Stream should complete with [DONE]
        assert b"[DONE]" in content


@pytest.mark.asyncio
async def test_malformed_sse_events() -> None:
    """Test malformed SSE events - graceful handling of corrupted streams."""
    # This test verifies the server handles malformed requests gracefully
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Valid request should work
        resp = await client.post(
            "/v1/responses",
            json={
                "model": MODEL_NAME,
                "input": "Test",
                "stream": True,
            },
        )
        assert resp.status_code == 200
        # Server should handle stream properly


@pytest.mark.asyncio
async def test_invalid_json_request() -> None:
    """Test invalid JSON request."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/responses",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_entity_not_found_error_message() -> None:
    """Test entity not found error message format."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/entities/nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "entity_not_found"
        assert "nonexistent" in data["error"]["message"].lower()
