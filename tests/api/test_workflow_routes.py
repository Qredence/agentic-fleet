from unittest.mock import AsyncMock, patch

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
async def test_health_check(async_client):
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_run_workflow(async_client):
    # Mock the workflow creation and execution
    mock_workflow = AsyncMock()
    mock_workflow.run.return_value = {
        "result": "Test result",
        "quality": {"score": 9.0},
        "metadata": {},
    }

    with patch(
        "agentic_fleet.api.routes.workflow.create_supervisor_workflow", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_workflow

        payload = {
            "workflow_id": "test-workflow",
            "inputs": {"task": "Test task for API", "config": {"max_rounds": 1}},
        }

        response = await async_client.post("/api/workflows/run", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["output"]["result"] == "Test result"
        assert data["output"]["quality_score"] == 9.0
