"""DSPy management router.

Provides endpoints for inspecting and managing DSPy modules.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from agentic_fleet.app.dependencies import WorkflowDep
from agentic_fleet.app.models.dspy import CacheInfo, ReasonerSummary
from agentic_fleet.app.services.dspy_service import DSPyService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dspy/prompts", response_model=dict[str, Any])
async def get_dspy_prompts(
    workflow: WorkflowDep,
) -> dict[str, Any]:
    """
    Retrieve DSPy predictors' prompts, signatures, fields, and demos.

    Builds a mapping from predictor name to a detail dictionary containing:
    - "instructions": predictor signature instructions (string)
    - "inputs": list of input field descriptors, each with keys `name`, `desc`, and `prefix`
    - "outputs": list of output field descriptors (same shape as inputs)
    - "demos_count": number of demos included
    - "demos": list of demo examples as dictionaries with stringified values

    Returns:
        prompts (dict[str, Any]): Mapping of predictor/module names to their prompt details.

    Raises:
        HTTPException: If the workflow has no DSPy reasoner (HTTP 404).
    """
    service = DSPyService(workflow)
    try:
        return service.get_predictor_prompts()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/dspy/config", response_model=dict[str, Any])
async def get_dspy_config(workflow: WorkflowDep) -> dict[str, Any]:
    """Retrieve DSPy configuration.

    Returns:
        Dictionary containing DSPy settings.
    """
    service = DSPyService(workflow)
    return service.get_config()


@router.get("/dspy/stats", response_model=dict[str, Any])
async def get_dspy_stats(workflow: WorkflowDep) -> dict[str, Any]:
    """Retrieve DSPy usage statistics.

    Returns:
        Dictionary containing usage stats.
    """
    service = DSPyService(workflow)
    return service.get_stats()


@router.get("/dspy/cache", response_model=CacheInfo)
async def get_cache_info_endpoint(workflow: WorkflowDep) -> CacheInfo:
    """Get information about the DSPy compilation cache.

    Returns cache metadata including creation time, size, and optimizer used.

    Returns:
        CacheInfo: Cache metadata or indication that no cache exists.
    """
    service = DSPyService(workflow)
    cache_info = service.get_cache_info()

    if cache_info is None:
        # Return a CacheInfo indicating no cache exists
        return CacheInfo(exists=False)

    # Convert cache info to CacheInfo model
    return CacheInfo(
        exists=True,
        created_at=cache_info.get("created_at"),
        cache_size_bytes=cache_info.get("cache_size_bytes"),
        optimizer=cache_info.get("optimizer"),
        signature_hash=cache_info.get("signature_hash"),
    )


@router.delete("/dspy/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache_endpoint(workflow: WorkflowDep) -> None:
    """Clear the DSPy compilation cache.

    Removes cached compiled modules, forcing recompilation on next use.
    """
    service = DSPyService(workflow)
    service.clear_cache()


@router.get("/dspy/reasoner/summary", response_model=ReasonerSummary)
async def get_reasoner_summary_endpoint(workflow: WorkflowDep) -> ReasonerSummary:
    """Get summary of DSPy reasoner state.

    Returns information about the reasoner's execution history,
    routing cache, and configuration.

    Returns:
        ReasonerSummary: Reasoner state summary.
    """
    service = DSPyService(workflow)
    summary = service.get_reasoner_summary()

    return ReasonerSummary(**summary)


@router.delete("/dspy/reasoner/routing-cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_routing_cache_endpoint(workflow: WorkflowDep) -> None:
    """Clear the DSPy reasoner's routing decision cache.

    Forces fresh routing decisions on next workflow execution.

    Raises:
        HTTPException: If the workflow has no DSPy reasoner (HTTP 404).
    """
    service = DSPyService(workflow)
    try:
        service.clear_routing_cache()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/dspy/signatures", response_model=dict[str, Any])
async def list_signatures_endpoint(workflow: WorkflowDep) -> dict[str, Any]:
    """List all available DSPy signatures.

    Returns information about all signature classes defined in the system,
    including their instructions, input fields, and output fields.

    Returns:
        dict: Mapping of signature names to their details.
    """
    service = DSPyService(workflow)
    return service.list_signatures()
