"""Tests for optimization and self-improvement endpoints."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from agentic_fleet.main import app


class TestOptimizeEndpoints:
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
        workflow.dspy_reasoner = MagicMock()
        workflow.context = MagicMock()
        workflow.config = MagicMock(
            dspy_model="gpt-5-mini",
            dspy_temperature=1.0,
            dspy_max_tokens=16000,
            examples_path="data/supervisor_examples.json",
        )

        def override_get_workflow():
            return workflow

        app.dependency_overrides[_get_workflow] = override_get_workflow
        yield workflow
        app.dependency_overrides = {}

    def test_optimize_starts_job_and_status_completes(self, client, mock_workflow):
        with patch("agentic_fleet.services.optimization_jobs._compile_all") as mock_compile:
            mock_compile.return_value = {
                "cache_paths": {"supervisor": ".var/logs/compiled_supervisor.pkl"}
            }

            response = client.post(
                "/api/v1/optimize",
                json={
                    "optimizer": "bootstrap",
                    "use_cache": True,
                    "gepa_auto": "light",
                    "harvest_history": False,
                    "min_quality": 8.0,
                },
            )

            assert response.status_code == status.HTTP_202_ACCEPTED
            job_id = response.json()["job_id"]
            assert job_id

            # Poll for completion (threaded job should finish quickly with mocked compile)
            last = None
            for _ in range(50):
                status_resp = client.get(f"/api/v1/optimize/{job_id}")
                assert status_resp.status_code == status.HTTP_200_OK
                last = status_resp.json()
                if last["status"] in ("completed", "failed"):
                    break
                time.sleep(0.01)

            assert last is not None
            assert last["status"] == "completed"

    def test_optimize_status_unknown_job(self, client):
        response = client.get("/api/v1/optimize/does-not-exist")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_self_improve_stats_only(self, client):
        with patch("agentic_fleet.api.routes.optimize.SelfImprovementEngine") as engine_cls:
            engine = engine_cls.return_value
            engine.get_improvement_stats.return_value = {"total_executions": 10}

            response = client.post("/api/v1/self-improve", json={"stats_only": True})
            assert response.status_code == status.HTTP_200_OK
            payload = response.json()
            assert payload["status"] == "completed"
            assert payload["stats"]["total_executions"] == 10

    def test_self_improve_adds_examples(self, client):
        with patch("agentic_fleet.api.routes.optimize.SelfImprovementEngine") as engine_cls:
            engine = engine_cls.return_value
            engine.get_improvement_stats.return_value = {"total_executions": 10}
            engine.analyze_and_improve.return_value = {"new_examples_added": 3}

            response = client.post(
                "/api/v1/self-improve",
                json={"stats_only": False, "min_quality": 8.0, "max_examples": 5},
            )
            assert response.status_code == status.HTTP_200_OK
            payload = response.json()
            assert payload["status"] == "completed"
            assert payload["new_examples_added"] == 3
