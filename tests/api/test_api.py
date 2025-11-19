from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from agentic_fleet.api.app import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@patch("agentic_fleet.api.routes.workflow.create_supervisor_workflow", new_callable=AsyncMock)
def test_run_workflow(mock_create_workflow):
    # Mock workflow instance
    mock_workflow = MagicMock()  # The workflow object itself is not async, its methods are
    mock_create_workflow.return_value = mock_workflow

    # Mock workflow run result
    mock_result = {
        "result": "Test Result",
        "quality": {"score": 9.5},
        "execution_summary": {"steps": 5},
        "metadata": {"mode": "test"},
    }
    mock_workflow.run = AsyncMock(return_value=mock_result)

    # Test request
    payload = {"task": "Test Task", "config": {"max_rounds": 10}}

    response = client.post("/workflow/run", json=payload)

    # Verification
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "Test Result"
    assert data["quality_score"] == 9.5
    assert data["execution_summary"] == {"steps": 5}

    # Verify mock calls
    mock_create_workflow.assert_called_once()
    mock_workflow.run.assert_called_once_with("Test Task")
