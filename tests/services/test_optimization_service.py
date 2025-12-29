import asyncio
from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.services.optimization_service import OptimizationService
from agentic_fleet.utils.storage.job_store import InMemoryJobStore


@pytest.mark.asyncio
async def test_submit_job_and_run():
    # Mock compile_reasoner to avoid running real logic
    with patch("agentic_fleet.services.optimization_service.compile_reasoner") as mock_compile:
        mock_compile.return_value = MagicMock()

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

        mock_compile.assert_called_once()


@pytest.mark.asyncio
async def test_submit_job_failure():
    # Mock compile_reasoner to raise exception
    with patch("agentic_fleet.services.optimization_service.compile_reasoner") as mock_compile:
        mock_compile.side_effect = ValueError("Optimization failed")

        service = OptimizationService(job_store=InMemoryJobStore())

        job_id = await service.submit_job(
            module="dummy_module", base_examples_path="dummy.json", user_id="test_user"
        )

        await asyncio.sleep(0.1)

        status = await service.get_job_status(job_id)
        assert status["status"] == "failed"
        assert status["error"] == "Optimization failed"
