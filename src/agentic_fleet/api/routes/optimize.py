"""Optimization and self-improvement routes."""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request, status

from agentic_fleet.api.deps import WorkflowDep
from agentic_fleet.models.dspy import (
    CompileRequest,
    OptimizationJobStatus,
    SelfImproveRequest,
    SelfImproveResponse,
)
from agentic_fleet.services.optimization_jobs import OptimizationJobManager
from agentic_fleet.utils.self_improvement import SelfImprovementEngine

router = APIRouter()


def _get_job_manager(request: Request) -> OptimizationJobManager:
    manager = getattr(request.app.state, "optimization_jobs", None)
    if manager is None:
        # Should be initialized in lifespan, but keep a safe fallback.
        manager = OptimizationJobManager()
        request.app.state.optimization_jobs = manager
    return cast(OptimizationJobManager, manager)


@router.post(
    "/optimize",
    response_model=OptimizationJobStatus,
    status_code=status.HTTP_202_ACCEPTED,
)
async def optimize(
    request: Request,
    body: CompileRequest,
    workflow: WorkflowDep,
) -> OptimizationJobStatus:
    """Start an optimization/compilation run in the background."""
    manager = _get_job_manager(request)
    job = manager.run_async(workflow=workflow, request=body)
    snap = job.snapshot()
    return OptimizationJobStatus(**snap)


@router.get("/optimize/{job_id}", response_model=OptimizationJobStatus)
async def optimize_status(request: Request, job_id: str) -> OptimizationJobStatus:
    """Get background optimization job status."""
    manager = _get_job_manager(request)
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization job {job_id} not found",
        )
    return OptimizationJobStatus(**job.snapshot())


@router.post("/self-improve", response_model=SelfImproveResponse)
async def self_improve(body: SelfImproveRequest) -> SelfImproveResponse:
    """Generate DSPy training examples from high-quality execution history."""
    engine = SelfImprovementEngine(
        min_quality_score=float(body.min_quality),
        max_examples_to_add=int(body.max_examples),
        history_lookback=100,
    )

    stats: dict[str, Any] = engine.get_improvement_stats()
    if body.stats_only:
        return SelfImproveResponse(
            status="completed",
            message="Stats computed",
            new_examples_added=0,
            stats=stats,
        )

    # API behavior: add examples but do NOT clear caches automatically.
    # This avoids degrading a running server that relies on compiled artifacts.
    result = engine.analyze_and_improve()
    added = int(result.get("new_examples_added", 0) or 0)

    if added <= 0:
        return SelfImproveResponse(
            status="no_op",
            message="No new high-quality examples found. Run more workflows to populate history.",
            new_examples_added=0,
            stats=stats,
        )

    return SelfImproveResponse(
        status="completed",
        message="Added new training examples. Run /optimize to compile updated artifacts.",
        new_examples_added=added,
        stats=stats,
    )
