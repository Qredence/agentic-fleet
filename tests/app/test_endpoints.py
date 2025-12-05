from unittest.mock import MagicMock

from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    # Enhanced health check returns status, checks, and version
    assert "status" in data
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data
    assert "api" in data["checks"]
    assert "version" in data


def test_run_workflow(client: TestClient, mock_workflow: MagicMock):
    mock_workflow.run.return_value = {
        "result": "Task completed",
        "status": "completed",
        "workflowId": "12345",
        "metadata": {"duration": "1s"},
    }

    payload = {"task": "Test task", "mode": "standard"}
    response = client.post("/api/v1/run", json=payload)

    assert response.status_code == 201  # 201 Created for successful workflow execution
    data = response.json()
    assert data["result"] == "Task completed"
    assert data["execution_id"] == "12345"

    mock_workflow.run.assert_called_once_with("Test task")


def test_get_agents(client: TestClient, mock_workflow: MagicMock):
    # Setup mock agents
    agent1 = MagicMock()
    agent1.name = "agent1"
    agent1.description = "Test Agent 1"
    agent1.type = "chat"

    agent2 = MagicMock()
    agent2.name = "agent2"
    agent2.description = "Test Agent 2"
    agent2.type = "specialist"

    mock_workflow.agents = {"agent1": agent1, "agent2": agent2}

    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "agent1"
    assert data[1]["name"] == "agent2"


def test_request_id_header(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    # header should be non-empty
    assert response.headers["X-Request-ID"].strip()


def test_get_history(client: TestClient, mock_workflow: MagicMock):
    mock_workflow.history_manager.get_recent_executions.return_value = [
        {"workflowId": "1", "task": "task1", "result": "res1"},
        {"workflowId": "2", "task": "task2", "result": "res2"},
    ]

    response = client.get("/api/v1/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["workflowId"] == "1"
