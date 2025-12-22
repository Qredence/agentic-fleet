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

    job_id = await service.submit_job(
        module=module_instance,
        base_examples_path=request.examples_path,
        user_id=request.user_id,
        auto_mode=request.auto_mode,
        **request.options,
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
