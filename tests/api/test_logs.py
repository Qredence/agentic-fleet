from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_log_file(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("")
    return log_file


@pytest.fixture
def mock_settings(temp_log_file):
    with patch("agentic_fleet.api.routes.logs.settings") as mock_settings:
        mock_settings.LOG_FILE_PATH = str(temp_log_file)
        # Also patch the module-level LOG_FILE constant if it was already initialized
        with patch("agentic_fleet.api.routes.logs.LOG_FILE", temp_log_file):
            yield mock_settings


def test_get_logs_empty(client: TestClient, mock_settings):
    response = client.get("/api/logs")
    assert response.status_code == 200
    data = response.json()
    assert data["logs"] == []


def test_get_logs_with_content(client: TestClient, mock_settings, temp_log_file):
    log_content = (
        "2023-10-27 10:00:00,000 - agentic_fleet.test - INFO - System started\n"
        "2023-10-27 10:00:01,000 - agentic_fleet.agent - WARNING - Agent warning\n"
        "2023-10-27 10:00:02,000 - agentic_fleet.error - ERROR - Critical failure\n"
    )
    temp_log_file.write_text(log_content)

    response = client.get("/api/logs")
    assert response.status_code == 200
    data = response.json()
    assert len(data["logs"]) == 3

    assert data["logs"][0]["level"] == "INFO"
    assert data["logs"][0]["message"] == "System started"
    assert data["logs"][2]["level"] == "ERROR"


def test_get_logs_filter_level(client: TestClient, mock_settings, temp_log_file):
    log_content = (
        "2023-10-27 10:00:00,000 - test - INFO - Info msg\n"
        "2023-10-27 10:00:01,000 - test - ERROR - Error msg\n"
    )
    temp_log_file.write_text(log_content)

    response = client.get("/api/logs?level=ERROR")
    assert response.status_code == 200
    data = response.json()
    assert len(data["logs"]) == 1
    assert data["logs"][0]["level"] == "ERROR"


def test_get_logs_filter_agent(client: TestClient, mock_settings, temp_log_file):
    log_content = (
        "2023-10-27 10:00:00,000 - test - INFO - AgentA: doing work\n"
        "2023-10-27 10:00:01,000 - test - INFO - AgentB: doing work\n"
    )
    temp_log_file.write_text(log_content)

    response = client.get("/api/logs?agent_id=AgentA")
    assert response.status_code == 200
    data = response.json()
    assert len(data["logs"]) == 1
    assert "AgentA" in data["logs"][0]["message"]


def test_get_logs_no_file(client: TestClient):
    # Patch LOG_FILE to a non-existent path
    with patch("agentic_fleet.api.routes.logs.LOG_FILE", Path("/non/existent/path.log")):
        response = client.get("/api/logs")
        assert response.status_code == 200
        assert response.json()["logs"] == []
