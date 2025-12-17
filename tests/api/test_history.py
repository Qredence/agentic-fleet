"""Tests for history endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from agentic_fleet.main import app


class TestHistoryEndpoints:
    """Tests for history management endpoints."""

    @pytest.fixture
    def client(self):
        with patch(
            "agentic_fleet.api.lifespan.create_supervisor_workflow", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock()
            with TestClient(app) as client:
                yield client

    @pytest.fixture
    def mock_workflow(self):
        from agentic_fleet.api.deps import _get_workflow

        workflow = MagicMock()

        def override_get_workflow():
            return workflow

        app.dependency_overrides[_get_workflow] = override_get_workflow
        yield workflow
        app.dependency_overrides = {}

    def test_get_history_pagination(self, client, mock_workflow):
        """Test history retrieval with pagination."""
        # Mock history manager
        manager = MagicMock()
        # Ensure get_recent doesn't exist so the router falls back to get_recent_executions
        del manager.get_recent
        mock_workflow.history_manager = manager

        # Mock get_recent_executions
        manager.get_recent_executions.return_value = [
            {"workflowId": "1"},
            {"workflowId": "2"},
        ]

        response = client.get("/api/v1/history?limit=10&offset=5")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2
        manager.get_recent_executions.assert_called_with(limit=10, offset=5)

    def test_get_execution_details(self, client, mock_workflow):
        """Test retrieving specific execution details."""
        manager = MagicMock()
        mock_workflow.history_manager = manager

        manager.get_execution.return_value = {"workflowId": "123", "status": "completed"}

        response = client.get("/api/v1/history/123")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["workflowId"] == "123"
        manager.get_execution.assert_called_with("123")

    def test_get_execution_not_found(self, client, mock_workflow):
        """Test retrieving non-existent execution."""
        manager = MagicMock()
        mock_workflow.history_manager = manager

        manager.get_execution.return_value = None

        response = client.get("/api/v1/history/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_execution(self, client, mock_workflow):
        """Test deleting an execution."""
        manager = MagicMock()
        mock_workflow.history_manager = manager

        manager.delete_execution.return_value = True

        response = client.delete("/api/v1/history/123")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        manager.delete_execution.assert_called_with("123")

    def test_delete_execution_not_found(self, client, mock_workflow):
        """Test deleting non-existent execution."""
        manager = MagicMock()
        mock_workflow.history_manager = manager

        manager.delete_execution.return_value = False

        response = client.delete("/api/v1/history/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_clear_history(self, client, mock_workflow):
        """Test clearing all history."""
        manager = MagicMock()
        mock_workflow.history_manager = manager

        response = client.delete("/api/v1/history")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        manager.clear_history.assert_called_once()
