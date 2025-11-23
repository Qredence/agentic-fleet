from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_history_manager():
    with patch("agentic_fleet.api.routes.history.HistoryManager") as mock_manager:
        instance = mock_manager.return_value
        yield instance


def test_get_history_empty(client: TestClient, mock_history_manager):
    mock_history_manager.load_history.return_value = []

    response = client.get("/api/history")
    assert response.status_code == 200
    data = response.json()
    assert data["runs"] == []


def test_get_history_with_data(client: TestClient, mock_history_manager):
    mock_data = [
        {
            "workflowId": "run-123",
            "task": "Test Task",
            "result": "Success",
            "routing": {"assigned_to": ["AgentA"]},
            "total_time_seconds": 1.5,
            "phase_timings": {"analysis": 0.1},
        }
    ]
    mock_history_manager.load_history.return_value = mock_data

    response = client.get("/api/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data["runs"]) == 1
    run = data["runs"][0]
    assert run["run_id"] == "run-123"
    assert run["task"] == "Test Task"
    # Default fields shouldn't include detailed routing/timing unless requested
    assert "routing" not in run
    assert "timing" not in run


def test_get_history_with_params(client: TestClient, mock_history_manager):
    mock_data = [
        {
            "workflowId": "run-123",
            "task": "Test Task",
            "result": "Success",
            "routing": {"assigned_to": ["AgentA"]},
            "total_time_seconds": 1.5,
            "phase_timings": {"analysis": 0.1},
        }
    ]
    mock_history_manager.load_history.return_value = mock_data

    # Request with all details
    response = client.get("/api/history?routing=true&agents=true&timing=true")
    assert response.status_code == 200
    data = response.json()
    run = data["runs"][0]

    assert "routing" in run
    assert "agents" in run
    assert run["agents"] == ["AgentA"]
    assert "timing" in run
    assert run["timing"]["total"] == 1.5


def test_get_history_error(client: TestClient, mock_history_manager):
    mock_history_manager.load_history.side_effect = Exception("DB Error")

    response = client.get("/api/history")
    assert response.status_code == 500
