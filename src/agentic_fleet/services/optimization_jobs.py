"""Background optimization job management for the API.

This module provides a lightweight in-memory job registry for DSPy compilation
and optimization operations triggered via FastAPI endpoints.

Note: This is process-local state (sufficient for single-process deployments and dev).
"""

from __future__ import annotations

import concurrent.futures
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from agentic_fleet.dspy_modules.lifecycle import configure_dspy_settings
from agentic_fleet.models.dspy import CompileRequest
from agentic_fleet.utils.cfg import DEFAULT_GEPA_LOG_DIR
from agentic_fleet.utils.compiler import compile_answer_quality, compile_nlu, compile_reasoner
from agentic_fleet.utils.logger import setup_logger
from agentic_fleet.utils.progress import NullProgressCallback, ProgressCallback

logger = setup_logger(__name__)

JobStatus = Literal["started", "running", "completed", "cached", "failed"]


@dataclass(slots=True)
class OptimizationJob:
    """Represents a single DSPy optimization job with thread-safe status tracking."""

    job_id: str
    status: JobStatus = "started"
    message: str = "Queued"
    cache_path: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    progress: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def snapshot(self) -> dict[str, Any]:
        """Return a thread-safe snapshot of the job's current state."""
        with self._lock:
            return {
                "job_id": self.job_id,
                "status": self.status,
                "message": self.message,
                "cache_path": self.cache_path,
                "started_at": self.started_at,
                "completed_at": self.completed_at,
                "error": self.error,
                "progress": self.progress,
                "details": self.details,
            }

    def update(self, **kwargs: Any) -> None:
        """Update job attributes in a thread-safe manner."""
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)


class _JobProgressCallback(ProgressCallback):
    def __init__(self, job: OptimizationJob) -> None:
        self.job = job

    def on_start(self, message: str) -> None:
        self.job.update(status="running", message=message)

    def on_progress(
        self, message: str, current: int | None = None, total: int | None = None
    ) -> None:
        progress: float | None = None
        if current is not None and total is not None and total > 0:
            try:
                progress = max(0.0, min(1.0, float(current) / float(total)))
            except Exception:
                progress = None
        self.job.update(message=message, progress=progress)

    def on_complete(self, message: str, duration: float | None = None) -> None:  # noqa: ARG002
        self.job.update(message=message)

    def on_error(self, message: str, error: Exception | None = None) -> None:
        self.job.update(
            status="failed",
            message=message,
            error=str(error) if error else message,
        )


def _build_gepa_options(request: CompileRequest) -> dict[str, Any]:
    # Minimal defaults mirroring CLI behavior while keeping the API small.
    options: dict[str, Any] = {
        "auto": request.gepa_auto,
        "log_dir": DEFAULT_GEPA_LOG_DIR,
        "perfect_score": 1.0,
        "use_history_examples": bool(request.harvest_history),
        "history_min_quality": float(request.min_quality),
        "history_limit": 200,
        "val_split": 0.2,
        "seed": 13,
    }
    # Ensure exactly one budget flag is set (compile_reasoner enforces this).
    if options.get("auto") is None:
        options["auto"] = "light"
    return options


def _compile_all(
    workflow: Any,
    request: CompileRequest,
    progress_callback: ProgressCallback,
    parallel: bool = False,
) -> dict[str, Any]:
    """Run compilation steps; designed to be patched in tests.

    Phase 4: Added parallel compilation support when parallel=True.

    Args:
        workflow: Workflow instance with dspy_reasoner
        request: Compilation request parameters
        progress_callback: Progress callback for updates
        parallel: Whether to run quality and NLU compilation in parallel

    Returns:
        Dictionary with cache paths for compiled modules
    """
    config = getattr(workflow, "config", None)
    dspy_reasoner = getattr(workflow, "dspy_reasoner", None)
    if dspy_reasoner is None:
        raise ValueError("DSPy reasoner not available on workflow")

    model = getattr(config, "dspy_model", None) or "gpt-5-mini"
    temperature = float(getattr(config, "dspy_temperature", 1.0))
    max_tokens = int(getattr(config, "dspy_max_tokens", 16000))

    # Ensure DSPy is configured for compilation calls.
    configure_dspy_settings(model=model, temperature=temperature, max_tokens=max_tokens)

    examples_path = getattr(config, "examples_path", None) or "data/supervisor_examples.json"

    gepa_options = None
    if request.optimizer == "gepa":
        gepa_options = _build_gepa_options(request)

    progress_callback.on_progress("Compiling supervisor reasoner...")
    compiled_supervisor = compile_reasoner(
        dspy_reasoner,
        examples_path=examples_path,
        use_cache=bool(request.use_cache),
        optimizer=str(request.optimizer),
        gepa_options=gepa_options,
        dspy_model=model,
        agent_config=None,
        progress_callback=progress_callback,
        allow_gepa_optimization=True,
    )

    # Hot-swap compiled supervisor into the workflow for subsequent runs.
    try:
        workflow.dspy_reasoner = compiled_supervisor
        if hasattr(workflow, "context"):
            workflow.context.dspy_supervisor = compiled_supervisor  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - best effort
        logger.debug("Failed to hot-swap compiled supervisor: %s", exc)

    # Phase 4: Compile quality and NLU in parallel when requested
    if parallel:
        progress_callback.on_progress("Compiling quality and NLU modules in parallel...")

        def compile_quality():
            compile_answer_quality(
                use_cache=bool(request.use_cache), progress_callback=NullProgressCallback()
            )
            try:
                from agentic_fleet.dspy_modules.answer_quality import clear_module_cache

                clear_module_cache()
            except Exception:
                pass

        def compile_nlu_module():
            compile_nlu(use_cache=bool(request.use_cache), progress_callback=NullProgressCallback())

        # Run in parallel using thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(compile_quality), executor.submit(compile_nlu_module)]
            concurrent.futures.wait(futures)

            # Check for exceptions
            for future in futures:
                if future.exception():
                    logger.warning("Parallel compilation error: %s", future.exception())
    else:
        # Sequential compilation (original behavior)
        progress_callback.on_progress("Compiling AnswerQualityModule...")
        compile_answer_quality(
            use_cache=bool(request.use_cache), progress_callback=progress_callback
        )
        try:
            from agentic_fleet.dspy_modules.answer_quality import clear_module_cache

            clear_module_cache()
        except Exception:
            pass

        progress_callback.on_progress("Compiling DSPyNLU...")
        compile_nlu(use_cache=bool(request.use_cache), progress_callback=progress_callback)

    return {
        "cache_paths": {
            "supervisor": ".var/logs/compiled_supervisor.pkl",
            "answer_quality": ".var/logs/compiled_answer_quality.pkl",
            "nlu": ".var/logs/compiled_nlu.pkl",
        }
    }


class OptimizationJobManager:
    """In-memory job registry for optimization operations."""

    def __init__(self) -> None:
        self._jobs: dict[str, OptimizationJob] = {}
        self._lock = threading.Lock()

    def create_job(self) -> OptimizationJob:
        """Create a new optimization job and register it in the manager."""
        job_id = str(uuid4())
        job = OptimizationJob(
            job_id=job_id,
            status="started",
            message="Queued",
            started_at=datetime.now().isoformat(),
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> OptimizationJob | None:
        """Retrieve a job by its ID, or None if not found."""
        with self._lock:
            return self._jobs.get(job_id)

    def run_async(self, *, workflow: Any, request: CompileRequest) -> OptimizationJob:
        """Start a new optimization job in a background thread."""
        job = self.create_job()

        def _runner() -> None:
            cb: ProgressCallback = _JobProgressCallback(job)
            try:
                cb.on_start("Optimization started")
                details = _compile_all(workflow, request, cb)
                job.update(
                    status="completed",
                    message="Optimization completed",
                    completed_at=datetime.now().isoformat(),
                    cache_path=".var/logs/compiled_supervisor.pkl",
                    details=details,
                    progress=1.0,
                )
            except Exception as exc:
                logger.exception("Optimization job failed: %s", exc)
                job.update(
                    status="failed",
                    message="Optimization failed",
                    completed_at=datetime.now().isoformat(),
                    error=str(exc),
                )

        thread = threading.Thread(target=_runner, name=f"optimize-{job.job_id}", daemon=True)
        thread.start()
        return job
