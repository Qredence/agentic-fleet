"""Tests for the NEW optimization API routes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from agentic_fleet.main import app
from agentic_fleet.services.optimization_service import (
    OptimizationService,
    get_optimization_service,
)


@pytest.fixture
def mock_optimization_service():
    """Create a mock optimization service."""
    service = AsyncMock(spec=OptimizationService)
    return service


@pytest.fixture
def client(mock_optimization_service):
    """Create a test client with mocked lifespan dependencies."""
    mock_settings = MagicMock()
    mock_settings.max_concurrent_workflows = 10
    mock_settings.conversations_path = ".var/data/conversations.json"

    # Override the FastAPI dependency
    app.dependency_overrides[get_optimization_service] = lambda: mock_optimization_service

    with (
        patch(
            "agentic_fleet.api.lifespan.create_supervisor_workflow", new_callable=AsyncMock
        ) as mock_create,
        patch("agentic_fleet.api.lifespan.load_config") as mock_conf,
        patch("agentic_fleet.api.lifespan.get_settings") as mock_get_sett,
    ):
        mock_create.return_value = MagicMock()
        mock_conf.return_value = {"dspy": {"require_compiled": False}}
        mock_get_sett.return_value = mock_settings
        with TestClient(app) as client:
            yield client

    # Clean up the override
    app.dependency_overrides.clear()


class TestOptimizationEndpoints:
    """Tests for Phase 5 Optimization API."""

    def test_create_optimization_job_success(self, client, mock_optimization_service):
        """Test successful job submission."""
        mock_optimization_service.submit_job.return_value = "job-123"
        mock_optimization_service.get_job_status.return_value = {
            "job_id": "job-123",
            "status": "pending",
            "created_at": "2024-01-01T00:00:00Z",
        }

        response = client.post(
            "/api/v1/optimization/jobs",
            json={
                "module_name": "DSPyReasoner",
                "auto_mode": "light",
                "user_id": "user-1",
                "options": {"seed": 42},
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["job_id"] == "job-123"
        assert data["status"] == "pending"

        mock_optimization_service.submit_job.assert_called_once()

    def test_create_optimization_job_invalid_module(self, client):
        """Test rejection of unknown modules."""
        response = client.post(
            "/api/v1/optimization/jobs", json={"module_name": "UnknownModule", "user_id": "user-1"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Only 'DSPyReasoner' optimization" in response.json()["detail"]

    def test_get_job_status_success(self, client, mock_optimization_service):
        """Test retrieving job status."""
        mock_optimization_service.get_job_status.return_value = {
            "job_id": "job-123",
            "status": "running",
            "created_at": "2024-01-01T00:00:00Z",
            "started_at": "2024-01-01T00:00:05Z",
        }

        response = client.get("/api/v1/optimization/jobs/job-123")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "running"

    def test_get_job_status_not_found(self, client, mock_optimization_service):
        """Test 404 for missing jobs."""
        mock_optimization_service.get_job_status.return_value = None

        response = client.get("/api/v1/optimization/jobs/non-existent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
