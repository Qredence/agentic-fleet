from __future__ import annotations

from collections.abc import Iterable

import pytest
from fastapi.testclient import TestClient

from agentic_fleet.api.app import create_app


@pytest.fixture
def client() -> Iterable[TestClient]:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_workflows_endpoint_lists_defined_workflows(client: TestClient) -> None:
    response = client.get("/v1/workflows")

    assert response.status_code == 200
    data = response.json()
    workflows = data["workflows"]
    workflow_ids = {item["id"] for item in workflows}
    assert workflow_ids == {"collaboration", "magentic_fleet"}


def test_workflows_endpoint_returns_specific_config(client: TestClient) -> None:
    response = client.get("/v1/workflows/magentic_fleet")

    assert response.status_code == 200
    config = response.json()
    assert config["id"] == "magentic_fleet"
    assert config["factory"] == "create_magentic_fleet_workflow"
    assert set(config["agents"].keys()) >= {"planner", "executor", "coder", "verifier", "generator"}
