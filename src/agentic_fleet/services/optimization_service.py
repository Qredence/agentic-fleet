"""Optimization Service.

Manages running GEPA optimization jobs in the background.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from agentic_fleet.utils.compiler import compile_reasoner
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
        gepa_options: dict[str, Any] | None = None,
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
                "gepa_options": gepa_options or {},
                **kwargs,
            },
        }
        await self.job_store.save_job(job_id, job_data)

        # Start background task
        task = asyncio.create_task(
            self._run_optimization(
                job_id, module, base_examples_path, auto_mode, gepa_options=gepa_options, **kwargs
            )
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
        gepa_options: dict[str, Any] | None = None,
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

            # Build gepa_options from kwargs and provided options
            effective_gepa_options = {
                "auto": auto_mode,
                **(gepa_options or {}),
                **kwargs,  # Allow kwargs to override gepa_options
            }

            # Create progress callback that updates job status
            # Note: This callback runs in a thread, so we use asyncio.run_coroutine_threadsafe
            # to safely update the async job store from the thread
            class JobProgressCallback:
                """Progress callback that updates job status in the store."""

                def __init__(
                    self, job_store: JobStore, job_id: str, loop: asyncio.AbstractEventLoop
                ):
                    self.job_store = job_store
                    self.job_id = job_id
                    self.loop = loop
                    self.last_update_time = datetime.now(UTC)
                    self._update_lock = asyncio.Lock()

                def _schedule_update(self, status_update: dict[str, Any]) -> None:
                    """Schedule an async job update from the thread."""

                    async def _update_job() -> None:
                        async with self._update_lock:
                            job = await self.job_store.get_job(self.job_id)
                            if job:
                                job.update(status_update)
                                await self.job_store.save_job(self.job_id, job)

                    # Schedule the coroutine in the event loop
                    try:
                        asyncio.run_coroutine_threadsafe(_update_job(), self.loop)
                    except RuntimeError:
                        # Event loop may have stopped or been closed; cannot update (shutdown path)
                        logger.warning("Event loop not running, cannot update job progress")

                def on_start(self, message: str) -> None:
                    """Called when optimization starts."""
                    self._schedule_update(
                        {
                            "progress_message": message,
                            "progress_updated_at": datetime.now(UTC).isoformat(),
                        }
                    )

                def on_progress(
                    self, message: str, current: int | None = None, total: int | None = None
                ) -> None:
                    """Called to report progress during optimization."""
                    # Throttle updates to avoid too frequent writes (max once per 5 seconds)
                    now = datetime.now(UTC)
                    if (now - self.last_update_time).total_seconds() < 5:
                        return
                    self.last_update_time = now

                    progress_data: dict[str, Any] = {
                        "progress_message": message,
                        "progress_updated_at": now.isoformat(),
                    }
                    if current is not None and total is not None:
                        progress_data["progress_current"] = current
                        progress_data["progress_total"] = total
                        progress_data["progress_percent"] = (
                            int((current / total) * 100) if total > 0 else 0
                        )

                    self._schedule_update(progress_data)

                def on_complete(self, message: str, duration: float | None = None) -> None:
                    """Called when optimization completes."""
                    progress_data: dict[str, Any] = {
                        "progress_message": message,
                        "progress_updated_at": datetime.now(UTC).isoformat(),
                        "progress_completed": True,
                    }
                    if duration is not None:
                        progress_data["progress_duration"] = duration
                    self._schedule_update(progress_data)

                def on_error(self, message: str, error: Exception | None = None) -> None:
                    """Called when optimization encounters an error."""
                    self._schedule_update(
                        {
                            "progress_message": message,
                            "progress_updated_at": datetime.now(UTC).isoformat(),
                            "progress_error": str(error) if error else message,
                        }
                    )

            # Get the current event loop to pass to the callback
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError as e:
                # _run_optimization is async and must have a running loop
                raise RuntimeError(
                    "No running event loop found. _run_optimization requires an active async context."
                ) from e

            progress_callback = JobProgressCallback(self.job_store, job_id, loop)

            # Run optimization using compile_reasoner which handles history harvesting
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
                compile_reasoner,
                module=module,
                examples_path=base_examples_path,
                use_cache=False,  # Don't use cache for API-triggered optimizations
                optimizer="gepa",
                gepa_options=effective_gepa_options,
                progress_callback=progress_callback,
                allow_gepa_optimization=True,
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
