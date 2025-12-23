"""DSPy management routes.

Provides endpoints for inspecting and managing DSPy modules.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from agentic_fleet.api.deps import WorkflowDep
from agentic_fleet.models import CacheInfo, ReasonerSummary
from agentic_fleet.services.dspy_service import DSPyService

router = APIRouter()


def get_dspy_service(workflow: WorkflowDep) -> DSPyService:
    """Get DSPyService instance for a workflow."""
    return DSPyService(workflow)


DSPyServiceDep = Annotated[DSPyService, Depends(get_dspy_service)]


@router.get("/dspy/prompts", response_model=dict[str, Any])
async def get_dspy_prompts(service: DSPyServiceDep) -> dict[str, Any]:
    """Retrieve DSPy predictors' prompts, signatures, fields, and demos."""
    try:
        return service.get_predictor_prompts()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/dspy/config", response_model=dict[str, Any])
async def get_dspy_config(service: DSPyServiceDep) -> dict[str, Any]:
    """Return the current DSPy configuration."""
    return service.get_config()


@router.get("/dspy/stats", response_model=dict[str, Any])
async def get_dspy_stats(service: DSPyServiceDep) -> dict[str, Any]:
    """Return basic DSPy usage statistics."""
    return service.get_stats()


@router.get("/dspy/cache", response_model=CacheInfo)
async def get_cache_info_endpoint(service: DSPyServiceDep) -> CacheInfo:
    """Return DSPy compilation cache metadata (or exists=False)."""
    cache_info = service.get_cache_info()
    if cache_info is None:
        return CacheInfo(exists=False)
    return CacheInfo(
        exists=True,
        created_at=cache_info.get("created_at"),
        cache_size_bytes=cache_info.get("cache_size_bytes"),
        optimizer=cache_info.get("optimizer"),
        signature_hash=cache_info.get("signature_hash"),
    )


@router.delete("/dspy/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache_endpoint(service: DSPyServiceDep) -> None:
    """Clear DSPy compilation cache artifacts."""
    service.clear_cache()


@router.get("/dspy/reasoner/summary", response_model=ReasonerSummary)
async def get_reasoner_summary_endpoint(service: DSPyServiceDep) -> ReasonerSummary:
    """Return a summary of DSPy reasoner state and caches."""
    summary = service.get_reasoner_summary()
    return ReasonerSummary(**summary)


@router.delete("/dspy/reasoner/routing-cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_routing_cache_endpoint(service: DSPyServiceDep) -> None:
    """Clear DSPy routing decision cache."""
    try:
        service.clear_routing_cache()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/dspy/signatures", response_model=dict[str, Any])
async def list_signatures_endpoint(service: DSPyServiceDep) -> dict[str, Any]:
    """List available DSPy signatures and their fields."""
    return service.list_signatures()
