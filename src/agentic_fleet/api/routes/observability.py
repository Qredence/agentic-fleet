"""Observability API routes."""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agentic_fleet.utils.infra.langfuse import get_langfuse_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/observability", tags=["observability"])


def sanitize_for_logging(text: str | None) -> str:
    """Sanitize potentially untrusted text for safe inclusion in log messages.

    This function removes control characters (including newlines) and restricts the
    remaining characters to a conservative, printable subset to prevent log
    injection and log forgery.

    Args:
        text: Text to sanitize (may be None)

    Returns:
        Sanitized text or empty string if None.
    """
    if text is None:
        return ""
    # Remove all control characters (0x00-0x1f includes CR, LF, tabs) and extended control (0x7f-0x9f)
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)
    # Collapse runs of whitespace to a single space
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Finally, drop any remaining characters outside a conservative safe set
    return re.sub(r"[^\w\-\.@:/ ]", "", cleaned)


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
            safe_workflow_id = sanitize_for_logging(workflow_id)
            raise HTTPException(status_code=404, detail=f"Trace {safe_workflow_id} not found.")

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
        safe_workflow_id = sanitize_for_logging(workflow_id)
        safe_error_msg = sanitize_for_logging(str(e))
        logger.error(f"Failed to fetch trace {safe_workflow_id}: {safe_error_msg}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching trace: {safe_error_msg}"
        ) from e


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
