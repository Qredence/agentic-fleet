"""Regression tests for workflow dependency handling."""

from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from agentic_fleet.api.routes.agents import router as agents_router


def test_uninitialized_workflow_returns_503() -> None:
    """Requests depending on the workflow should fail fast when not initialized."""

    app = FastAPI()
    app.include_router(agents_router, prefix="/api/v1")

    with TestClient(app) as client:
        response = client.get("/api/v1/agents")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["detail"] == "Workflow not initialized. Service unavailable."
