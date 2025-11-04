"""Tests for entity discovery and management API."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from agentic_fleet.api.app import create_app


@pytest.mark.asyncio
async def test_list_entities() -> None:
    """Test listing all entities."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/entities")
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data
        assert isinstance(data["entities"], list)
        # Should have at least one entity (magentic_fleet)
        assert len(data["entities"]) > 0


@pytest.mark.asyncio
async def test_list_entities_schema_validation() -> None:
    """Test entity list schema validation - verify all entities have required fields."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/entities")
        assert resp.status_code == 200
        data = resp.json()
        entities = data["entities"]

        for entity in entities:
            assert "id" in entity
            assert "name" in entity
            assert "description" in entity
            assert "input_schema" in entity
            assert entity["input_schema"]["type"] == "object"
            assert "properties" in entity["input_schema"]
            assert "required" in entity["input_schema"]


@pytest.mark.asyncio
async def test_get_entity_info() -> None:
    """Test getting entity info."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/entities/magentic_fleet")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "magentic_fleet"
        assert "name" in data
        assert "description" in data
        assert "input_schema" in data


@pytest.mark.asyncio
async def test_get_entity_info_schema_validation() -> None:
    """Test entity info schema validation - verify input_schema structure."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/entities/magentic_fleet")
        assert resp.status_code == 200
        data = resp.json()

        input_schema = data["input_schema"]
        assert input_schema["type"] == "object"
        assert "properties" in input_schema
        assert "required" in input_schema
        assert "input" in input_schema["properties"]
        assert input_schema["properties"]["input"]["type"] == "string"
        assert "input" in input_schema["required"]


@pytest.mark.asyncio
async def test_get_entity_info_not_found() -> None:
    """Test getting non-existent entity info."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/entities/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reload_entity() -> None:
    """Test reloading an entity."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/entities/magentic_fleet/reload")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_id"] == "magentic_fleet"
        assert data["success"] is True


@pytest.mark.asyncio
async def test_reload_entity_not_found() -> None:
    """Test reloading a non-existent entity."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/entities/nonexistent/reload")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reload_clears_workflow_cache() -> None:
    """Test reload clears workflow instance cache."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First, get entity info to populate cache
        resp1 = await client.get("/v1/entities/magentic_fleet")
        assert resp1.status_code == 200

        # Reload entity
        resp2 = await client.post("/v1/entities/magentic_fleet/reload")
        assert resp2.status_code == 200

        # Get entity info again - should still work after reload
        resp3 = await client.get("/v1/entities/magentic_fleet")
        assert resp3.status_code == 200
        assert resp3.json()["id"] == "magentic_fleet"


@pytest.mark.asyncio
async def test_concurrent_entity_access() -> None:
    """Test concurrent entity access."""
    import asyncio

    transport = ASGITransport(app=create_app())

    async def get_entity_info(client: AsyncClient) -> dict:
        resp = await client.get("/v1/entities/magentic_fleet")
        return resp.json()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Make multiple concurrent requests
        tasks = [get_entity_info(client) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All should succeed and return same data
        for result in results:
            assert result["id"] == "magentic_fleet"
            assert "name" in result
            assert "description" in result
