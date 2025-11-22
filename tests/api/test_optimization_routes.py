from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agentic_fleet.api.main import app


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_improvement_stats(async_client):
    mock_stats = {
        "total_executions": 100,
        "high_quality_executions": 20,
        "potential_new_examples": 5,
        "average_quality_score": 8.5,
        "quality_score_distribution": {"excellent": 10, "good": 10},
    }

    # Patch the SelfImprovementEngine class/methods
    with patch("agentic_fleet.api.routes.optimization.SelfImprovementEngine") as mock_engine:
        instance = mock_engine.return_value
        instance.get_improvement_stats.return_value = mock_stats

        response = await async_client.get("/api/optimization/stats?min_quality=8.0&lookback=50")

        assert response.status_code == 200
        data = response.json()
        assert data["total_executions"] == 100
        assert data["high_quality_executions"] == 20
        assert data["average_quality_score"] == 8.5

        # Verify engine was initialized with correct params
        # Note: args from query params are floats/ints
        mock_engine.assert_called_with(min_quality_score=8.0, history_lookback=50)


@pytest.mark.asyncio
async def test_run_self_improvement(async_client):
    with patch("agentic_fleet.api.routes.optimization.SelfImprovementEngine") as mock_engine:
        instance = mock_engine.return_value
        instance.auto_improve.return_value = (3, "Added 3 examples")

        payload = {
            "min_quality_score": 8.5,
            "max_examples": 10,
            "lookback": 200,
            "force_recompile": False,
        }

        response = await async_client.post("/api/optimization/run", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["added_examples"] == 3
        assert data["status"] == "Added 3 examples"

        # Verify initialization and method call
        mock_engine.assert_called_with(
            min_quality_score=8.5, max_examples_to_add=10, history_lookback=200
        )
        instance.auto_improve.assert_called_with(force_recompile=False)


@pytest.mark.asyncio
async def test_run_self_improvement_defaults(async_client):
    with patch("agentic_fleet.api.routes.optimization.SelfImprovementEngine") as mock_engine:
        instance = mock_engine.return_value
        instance.auto_improve.return_value = (0, "No examples")

        # Empty payload should use defaults from model
        response = await async_client.post("/api/optimization/run", json={})

        assert response.status_code == 200

        # Verify defaults
        # SelfImprovementRequest defaults: min_quality=8.0, max_examples=20, lookback=100, force_recompile=True
        mock_engine.assert_called_with(
            min_quality_score=8.0, max_examples_to_add=20, history_lookback=100
        )
        instance.auto_improve.assert_called_with(force_recompile=True)


@pytest.mark.asyncio
async def test_get_improvement_stats_error(async_client):
    with patch("agentic_fleet.api.routes.optimization.SelfImprovementEngine") as mock_engine:
        instance = mock_engine.return_value
        instance.get_improvement_stats.side_effect = Exception("DB Error")

        response = await async_client.get("/api/optimization/stats")

        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve improvement statistics" in data["detail"]
