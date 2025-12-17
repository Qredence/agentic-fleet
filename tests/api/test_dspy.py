"""Tests for DSPy management endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from agentic_fleet.main import app


class TestDSPyEndpoints:
    """Tests for DSPy introspection endpoints."""

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

    def test_get_prompts(self, client, mock_workflow):
        """Test retrieving DSPy prompts."""
        # Mock DSPy reasoner
        reasoner = MagicMock()
        mock_workflow.dspy_reasoner = reasoner

        # Mock named_predictors
        predictor = MagicMock()
        predictor.signature.instructions = "Test instructions"
        predictor.signature.fields = {"input": MagicMock(), "output": MagicMock()}
        predictor.signature.input_fields = {"input": MagicMock()}
        predictor.signature.output_fields = {"output": MagicMock()}
        predictor.demos = []

        reasoner.named_predictors.return_value = [("test_module", predictor)]

        response = client.get("/api/v1/dspy/prompts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "test_module" in data
        assert data["test_module"]["instructions"] == "Test instructions"

    def test_get_config(self, client, mock_workflow):
        """Test retrieving DSPy config."""
        # We don't need to mock much here as it reads global dspy settings
        # but we need workflow dependency to pass
        mock_workflow.dspy_reasoner = MagicMock()

        response = client.get("/api/v1/dspy/config")

        assert response.status_code == status.HTTP_200_OK
        assert "lm_provider" in response.json()

    def test_get_stats(self, client, mock_workflow):
        """Test retrieving DSPy stats."""
        mock_workflow.dspy_reasoner = MagicMock()

        response = client.get("/api/v1/dspy/stats")

        assert response.status_code == status.HTTP_200_OK
        assert "history_count" in response.json()
