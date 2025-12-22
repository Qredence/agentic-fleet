"""Optimization Service.

Manages running GEPA optimization jobs in the background.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from agentic_fleet.dspy_modules.optimizer import optimize_with_gepa, prepare_gepa_datasets
from agentic_fleet.utils.storage.job_store import InMemoryJobStore, JobStore

logger = logging.getLogger(__name__)

OptimizationMode = Literal["light", "medium", "heavy"]


class OptimizationService:
    """Service for managing DSPy optimization jobs."""

    def __init__(self, job_store: JobStore | None = None) -> None:
        self.job_store = job_store or InMemoryJobStore()
        self._background_tasks: set[asyncio.Task[Any]] = set()

    async def submit_job(
        self,
        module: Any,
        base_examples_path: str,
        user_id: str,
        auto_mode: OptimizationMode = "light",
        **kwargs: Any,
    ) -> str:
        """
        Submit a new optimization job.

        Args:
            module: The DSPy module to optimize (must be picklable or reconstructible).
                    For now, passing the actual object instance.
            base_examples_path: Path to training data.
            user_id: ID of the user triggering the job.
            auto_mode: GEPA auto mode ("light", "medium", "heavy").
            **kwargs: Additional args for optimize_with_gepa.

        Returns:
            Job ID.
        """
        job_id = str(uuid.uuid4())
        job_data = {
            "status": "pending",
            "user_id": user_id,
            "created_at": datetime.now(UTC).isoformat(),
            "config": {
                "auto_mode": auto_mode,
                "base_examples_path": base_examples_path,
                **kwargs,
            },
        }
        await self.job_store.save_job(job_id, job_data)

        # Start background task
        task = asyncio.create_task(
            self._run_optimization(job_id, module, base_examples_path, auto_mode, **kwargs)
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        return job_id

    async def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Get the status of a job."""
        job = await self.job_store.get_job(job_id)
        if not job:
            return None
        if "job_id" not in job:
            job["job_id"] = job.get("id", job_id)
        return job

    async def _run_optimization(
        self,
        job_id: str,
        module: Any,
        base_examples_path: str,
        auto_mode: OptimizationMode,
        **kwargs: Any,
    ) -> None:
        """
        Execute a GEPA optimization job in the background while updating and persisting job state.
        
        Prepares training and validation datasets, runs the optimization using the provided module and mode, and updates the job record with status transitions ("running", "completed", "failed"), timestamps, result artifact path, and any error message.
        
        Parameters:
            job_id (str): Identifier of the job to update and persist.
            module (Any): The model/module to optimize.
            base_examples_path (str): Filesystem path containing example data used to build datasets.
            auto_mode (OptimizationMode): Optimization mode to apply ("light", "medium", or "heavy").
            **kwargs: Additional options passed to dataset preparation or the optimizer (commonly includes `seed` and optimizer-specific flags).
        
        Returns:
            None
        """
        try:
            # Update status to running
            job = await self.job_store.get_job(job_id)
            if job:
                job["status"] = "running"
                job["started_at"] = datetime.now(UTC).isoformat()
                await self.job_store.save_job(job_id, job)

            # Prepare data
            trainset, valset = prepare_gepa_datasets(
                base_examples_path=base_examples_path,
                seed=kwargs.get("seed", 42),
            )

            # Run optimization
            # ⚠️ PERFORMANCE WARNING: CPU-intensive GEPA optimization
            # 
            # Current implementation uses asyncio.to_thread() which runs in the default
            # thread pool executor. This has limitations:
            # 
            # 1. Thread pool has a default size limit (typically 32 threads on most systems)
            # 2. CPU-bound work in threads still competes for GIL, degrading performance
            # 3. Multiple concurrent optimizations will starve other async operations
            # 4. No built-in rate limiting or resource control
            # 
            # PRODUCTION RECOMMENDATION: Use a proper task queue system:
            # - Celery with Redis/RabbitMQ for distributed task execution
            # - Ray for Python-native distributed computing
            # - Azure Container Jobs for serverless batch processing
            # 
            # For now, consider adding:
            # - Semaphore to limit concurrent optimizations (e.g., max 2-3)
            # - ProcessPoolExecutor instead of ThreadPoolExecutor
            # - Job queue with priority levels
            await asyncio.to_thread(
                optimize_with_gepa,
                module=module,
                trainset=trainset,
                valset=valset,
                auto=auto_mode,
                log_dir=f".var/logs/gepa/{job_id}",
                **kwargs,
            )

            # Save result (in a real app, we'd save the weights/artifact path)
            # For now just marking complete
            job = await self.job_store.get_job(job_id)
            if job:
                job["status"] = "completed"
                job["completed_at"] = datetime.now(UTC).isoformat()
                job["result_artifact_path"] = f".var/logs/gepa/{job_id}/compiled.json"
                # job["metrics"] = ... (could extract from logs)
                await self.job_store.save_job(job_id, job)

            logger.info(f"Optimization job {job_id} completed successfully.")

        except Exception as e:
            logger.error(f"Optimization job {job_id} failed: {e}", exc_info=True)
            job = await self.job_store.get_job(job_id)
            if job:
                job["status"] = "failed"
                job["error"] = str(e)
                job["failed_at"] = datetime.now(UTC).isoformat()
                await self.job_store.save_job(job_id, job)


# Singleton instance
_service: OptimizationService | None = None


def get_optimization_service() -> OptimizationService:
    """Get the singleton optimization service."""
    global _service
    if _service is None:
        _service = OptimizationService()
    return _service