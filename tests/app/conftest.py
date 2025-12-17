from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agentic_fleet.api.deps import get_workflow
from agentic_fleet.main import app
from agentic_fleet.workflows.supervisor import SupervisorWorkflow


@pytest.fixture
def mock_workflow():
    workflow = MagicMock(spec=SupervisorWorkflow)
    workflow.run = AsyncMock()
    workflow.agents = {"agent1": MagicMock(name="agent1"), "agent2": MagicMock(name="agent2")}
    workflow.history_manager = MagicMock()
    workflow.history_manager.get_recent.return_value = [{"id": "1", "task": "test"}]
    return workflow


@pytest.fixture
def client(mock_workflow):
    app.dependency_overrides[get_workflow] = lambda: mock_workflow

    # Patch create_supervisor_workflow to prevent real initialization during startup
    with patch(
        "agentic_fleet.api.lifespan.create_supervisor_workflow", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_workflow
        with TestClient(app) as client:
            yield client

    app.dependency_overrides.clear()
