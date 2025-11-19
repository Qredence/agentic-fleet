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
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_run_workflow(async_client):
    # Mock request
    # payload = {"task": "Test task for API", "config": {"max_rounds": 1}}

    # Note: This test executes the actual workflow logic.
    # In a unit test environment without full OpenAI keys, this might fail or need mocking.
    # For now, we expect at least a 200 or a handled 500 if keys are missing.
    # We will mock the create_supervisor_workflow to avoid actual API calls

    # TODO: Add proper mocking for create_supervisor_workflow
    pass


@pytest.mark.asyncio
async def test_list_agents(async_client):
    response = await async_client.get("/api/v1/workflow/agents")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert len(data["agents"]) > 0
    assert data["agents"][0]["name"] == "Researcher"


@pytest.mark.asyncio
async def test_optimize_endpoint(async_client):
    # Trigger optimization
    payload = {"iterations": 1, "task": "Simple benchmark", "compile_dspy": False}
    response = await async_client.post("/api/v1/workflow/optimize", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    job_id = data["optimization_id"]

    # Check status
    status_response = await async_client.get(f"/api/v1/workflow/optimize/{job_id}")
    assert status_response.status_code == 200
    assert status_response.json()["optimization_id"] == job_id
