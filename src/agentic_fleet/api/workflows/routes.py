"""Routes for workflow management (listing and config retrieval)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from agentic_fleet.api.exceptions import WorkflowNotFoundError
from agentic_fleet.utils.factory import get_workflow_factory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows")


@router.get("")  # type: ignore[misc]
async def list_workflows() -> dict[str, Any]:
    """Return metadata for all available workflows.

    Ensures each workflow config is serialized via Pydantic's model_dump()/dict()
    for backward-compatible JSON shape used in tests.
    """
    factory = await get_workflow_factory()
    workflows = await factory.list_available_workflows_async()
    serialized: list[dict[str, Any]] = []
    for w in workflows:
        if hasattr(w, "model_dump"):
            serialized.append(w.model_dump())  # type: ignore
        elif hasattr(w, "dict"):
            serialized.append(w.dict())  # type: ignore
        else:
            # Already a dict-like structure
            serialized.append(w)  # type: ignore
    return {"workflows": serialized}


@router.get("/{workflow_id}")  # type: ignore
async def get_workflow_config(workflow_id: str) -> dict[str, Any]:
    """Return configuration for a specific workflow.

    Uses model_dump() instead of dataclasses.asdict() because WorkflowConfig
    is a Pydantic model, not a dataclass.
    """
    factory = await get_workflow_factory()
    try:
        config = await factory.get_workflow_config_async(workflow_id)
    except ValueError as exc:
        raise WorkflowNotFoundError(workflow_id) from exc
    return config.model_dump() if hasattr(config, "model_dump") else dict(config)
