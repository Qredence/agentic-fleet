"""Observability API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agentic_fleet.utils.infra.langfuse import get_langfuse_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/observability", tags=["observability"])


class TraceDetails(BaseModel):
    """Trace details response model."""

    id: str
    timestamp: str
    name: str | None = None
    user_id: str | None = Field(None, alias="userId")
    session_id: str | None = Field(None, alias="sessionId")
    metadata: dict[str, Any] | None = None
    input: Any | None = None
    output: Any | None = None
    observations: list[dict[str, Any]] = []
    scores: list[dict[str, Any]] = []

    class Config:
        """Pydantic config."""

        allow_population_by_field_name = True


@router.get("/trace/{workflow_id}", response_model=TraceDetails)
async def get_workflow_trace(workflow_id: str) -> dict[str, Any]:
    """Fetch full trace details from Langfuse.

    Args:
        workflow_id: The workflow execution ID (mapped to Langfuse trace_id)

    Returns:
        Trace details including all spans and observations
    """
    try:
        langfuse = get_langfuse_client()
        if not langfuse:
            raise HTTPException(status_code=503, detail="Langfuse integration is not configured.")

        # Fetch trace details
        # Note: Langfuse SDK returns a Pydantic-like object or dict depending on version
        # The fetch_trace method returns a Trace object which can be converted to dict
        trace = langfuse.fetch_trace(workflow_id)

        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace {workflow_id} not found.")

        # Convert to a stable response format
        # We want to flatten some properties and ensure observations are included
        # fetch_trace typically includes observations if requested or by default in some versions
        # If not, we may need to fetch them separately

        trace_dict = trace.dict() if hasattr(trace, "dict") else vars(trace)

        # Ensure observations and scores are serialized correctly
        if hasattr(trace, "observations") and not trace_dict.get("observations"):
            trace_dict["observations"] = [
                o.dict() if hasattr(o, "dict") else vars(o) for o in trace.observations
            ]

        if hasattr(trace, "scores") and not trace_dict.get("scores"):
            trace_dict["scores"] = [
                s.dict() if hasattr(s, "dict") else vars(s) for s in trace.scores
            ]

        return trace_dict

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch trace {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching trace: {e!s}") from e


@router.get("/traces")
async def list_recent_traces(limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
    """List recent traces for the dashboard."""
    try:
        langfuse = get_langfuse_client()
        if not langfuse:
            return []

        traces = langfuse.fetch_traces(limit=limit, offset=offset)
        return [t.dict() if hasattr(t, "dict") else vars(t) for t in traces.data]
    except Exception as e:
        logger.error(f"Failed to list traces: {e}")
        return []
