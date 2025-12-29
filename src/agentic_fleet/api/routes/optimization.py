"""Optimization API Routes.

Endpoints for managing GEPA optimization jobs.
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from agentic_fleet.services.optimization_service import (
    OptimizationService,
    get_optimization_service,
)
from agentic_fleet.utils.cfg import DEFAULT_EXAMPLES_PATH

router = APIRouter(prefix="/optimization", tags=["optimization"])

OptimizationServiceDep = Annotated[OptimizationService, Depends(get_optimization_service)]


class OptimizationRequest(BaseModel):
    """Request to start an optimization job."""

    module_name: str = Field(..., description="Name of the DSPy module to optimize")
    auto_mode: Literal["light", "medium", "heavy"] = "light"
    examples_path: str = Field(
        default=DEFAULT_EXAMPLES_PATH, description="Path to training examples"
    )
    user_id: str = Field(..., description="User ID for the job")
    # History options
    use_history_examples: bool = Field(
        default=False, description="Use execution history as training data"
    )
    history_min_quality: float = Field(
        default=8.0,
        ge=0.0,
        le=10.0,
        description="Minimum quality score (0-10) for history examples",
    )
    history_limit: int = Field(
        default=200, ge=1, description="Maximum number of history entries to harvest"
    )
    options: dict[str, Any] = Field(default_factory=dict, description="Additional options")


class JobStatusResponse(BaseModel):
    """Response for job status."""

    job_id: str
    status: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    result_artifact: str | None = None
    # Progress fields
    progress_message: str | None = None
    progress_updated_at: str | None = None
    progress_current: int | None = None
    progress_total: int | None = None
    progress_percent: int | None = None
    progress_completed: bool = False
    progress_duration: float | None = None


@router.post("/jobs", response_model=JobStatusResponse)
async def create_optimization_job(
    request: OptimizationRequest,
    service: OptimizationServiceDep,
) -> dict[str, Any]:
    """
    Start a new optimization job.
    """
    # In a real app, we'd dynamically load the module here or use a registry.
    # For safety/simplicity in this demo, we might restrict it or mock it.
    # We'll assume the module is the 'DSPyReasoner' for now as it's the main target.
    from agentic_fleet.dspy_modules.reasoner import DSPyReasoner

    if request.module_name != "DSPyReasoner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only 'DSPyReasoner' optimization is currently supported via API.",
        )

    # We need an instance to compile.
    # Note: Creating a fresh instance for optimization.
    # In a real scenario, we might want to load a specific version or configuration.
    module_instance = DSPyReasoner()

    # Ensure modules are initialized before optimization
    # This is critical for GEPA to access predictor signatures correctly
    module_instance._ensure_modules_initialized()

    # Build gepa_options from request
    gepa_options = {
        **request.options,
        "use_history_examples": request.use_history_examples,
        "history_min_quality": request.history_min_quality,
        "history_limit": request.history_limit,
    }

    job_id = await service.submit_job(
        module=module_instance,
        base_examples_path=request.examples_path,
        user_id=request.user_id,
        auto_mode=request.auto_mode,
        gepa_options=gepa_options,
    )

    # Return initial status
    job = await service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=500, detail="Failed to create job")

    return job


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    service: OptimizationServiceDep,
) -> dict[str, Any]:
    """Get the status of an optimization job."""
    job = await service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
