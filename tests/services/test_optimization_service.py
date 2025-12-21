import asyncio
from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.services.optimization_service import OptimizationService
from agentic_fleet.utils.storage.job_store import InMemoryJobStore


@pytest.mark.asyncio
async def test_submit_job_and_run():
    # Mock optimize_with_gepa to avoid running real logic
    with patch("agentic_fleet.services.optimization_service.optimize_with_gepa") as mock_optimize:
        mock_optimize.return_value = MagicMock()

        # Mock prepare_gepa_datasets
        with patch(
            "agentic_fleet.services.optimization_service.prepare_gepa_datasets"
        ) as mock_prep:
            mock_prep.return_value = ([], [])

            service = OptimizationService(job_store=InMemoryJobStore())

            job_id = await service.submit_job(
                module="dummy_module",
                base_examples_path="dummy.json",
                user_id="test_user",
                auto_mode="light",
            )

            assert job_id

            # Allow background task to potentially start/finish
            # Since create_task schedules it, we yield to event loop
            await asyncio.sleep(0.1)

            status = await service.get_job_status(job_id)
            assert status is not None
            # It should be completed because mocks return immediately
            assert status["status"] == "completed"
            assert status["user_id"] == "test_user"
            assert "completed_at" in status

            mock_optimize.assert_called_once()
            mock_prep.assert_called_once()


@pytest.mark.asyncio
async def test_submit_job_failure():
    # Mock optimize_with_gepa to raise exception
    with patch("agentic_fleet.services.optimization_service.optimize_with_gepa") as mock_optimize:
        mock_optimize.side_effect = ValueError("Optimization failed")

        with patch(
            "agentic_fleet.services.optimization_service.prepare_gepa_datasets"
        ) as mock_prep:
            mock_prep.return_value = ([], [])

            service = OptimizationService(job_store=InMemoryJobStore())

            job_id = await service.submit_job(
                module="dummy_module", base_examples_path="dummy.json", user_id="test_user"
            )

            await asyncio.sleep(0.1)

            status = await service.get_job_status(job_id)
            assert status["status"] == "failed"
            assert status["error"] == "Optimization failed"
