"""Optimization API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from agentic_fleet.api.models import (
    ImprovementStats,
    SelfImprovementRequest,
    SelfImprovementResponse,
)
from agentic_fleet.utils.logger import setup_logger
from agentic_fleet.utils.self_improvement import SelfImprovementEngine

router = APIRouter()
logger = setup_logger(__name__)


@router.get("/stats", response_model=ImprovementStats)
async def get_improvement_stats(
    min_quality: float = 8.0,
    lookback: int = 100,
) -> ImprovementStats:
    """
    Get statistics about potential for self-improvement.
    """
    try:
        engine = SelfImprovementEngine(
            min_quality_score=min_quality,
            history_lookback=lookback,
        )
        stats = engine.get_improvement_stats()

        # Map dictionary to Pydantic model
        return ImprovementStats(
            total_executions=stats.get("total_executions", 0),
            high_quality_executions=stats.get("high_quality_executions", 0),
            potential_new_examples=stats.get("potential_new_examples", 0),
            average_quality_score=stats.get("average_quality_score", 0.0),
            quality_score_distribution=stats.get("quality_score_distribution", {}),
        )
    except Exception as e:
        logger.exception("Failed to get improvement stats")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve improvement statistics: {e!s}",
        ) from e


@router.post("/run", response_model=SelfImprovementResponse)
async def run_self_improvement(
    request: SelfImprovementRequest,
) -> SelfImprovementResponse:
    """
    Trigger the self-improvement cycle.
    analyzes execution history, generates new training examples,
    and optionally forces recompilation of DSPy modules.
    """
    try:
        engine = SelfImprovementEngine(
            min_quality_score=request.min_quality_score,
            max_examples_to_add=request.max_examples,
            history_lookback=request.lookback,
        )

        added, status_msg = engine.auto_improve(force_recompile=request.force_recompile)

        return SelfImprovementResponse(
            added_examples=added,
            status=status_msg,
        )
    except Exception as e:
        logger.exception("Self-improvement cycle failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Self-improvement cycle failed: {e!s}",
        ) from e
