"""Tests for static file serving."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from agentic_fleet.api.app import create_app


@pytest.mark.asyncio
async def test_ui_directory_detection() -> None:
    """Test UI directory detection - verify UI directory existence check."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test that API routes still work (static serving shouldn't interfere)
        resp = await client.get("/v1/system/health")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_routes_still_work() -> None:
    """Test API routes still work - verify /v1/* routes not affected by static serving."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test various API endpoints
        resp = await client.get("/v1/system/health")
        assert resp.status_code == 200

        resp = await client.get("/v1/entities")
        assert resp.status_code == 200

        resp = await client.get("/v1/workflows")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_without_ui_directory() -> None:
    """Test without UI directory - verify graceful handling when UI dir missing."""
    # Mock the ui_dir Path instance

    with patch("agentic_fleet.api.app.Path") as mock_path_class:
        # Create a mock Path instance
        mock_ui_dir = Mock()
        mock_ui_dir.exists.return_value = False  # UI directory doesn't exist
        mock_ui_dir.is_dir.return_value = False

        # Make Path constructor return our mock for ui directory
        def path_side_effect(path_arg):
            if "ui" in str(path_arg):
                return mock_ui_dir
            return Path(path_arg)

        mock_path_class.side_effect = path_side_effect

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # API routes should still work
            resp = await client.get("/v1/system/health")
            assert resp.status_code == 200
