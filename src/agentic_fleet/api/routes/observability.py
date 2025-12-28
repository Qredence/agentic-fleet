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


def _convert_langfuse_object_to_dict(obj: Any) -> dict[str, Any]:
    """
    Convert a Langfuse SDK object to a dictionary with proper serialization.

    This handles different SDK versions by checking for known serialization methods
    and falls back to a limited set of safe attributes rather than exposing all
    internal implementation details via vars().

    Args:
        obj: Langfuse SDK object (e.g., Trace, Observation, Score)

    Returns:
        Dictionary representation of the object

    Raises:
        ValueError: If the object cannot be safely serialized
    """
    # Try standard serialization methods first
    if hasattr(obj, "dict") and callable(obj.dict):
        return obj.dict()
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        return obj.model_dump()

    # Fallback: extract only known safe attributes
    # These are common public fields across Langfuse SDK versions
    safe_attrs = {
        "id",
        "name",
        "user_id",
        "session_id",
        "metadata",
        "input",
        "output",
        "start_time",
        "end_time",
        "status_message",
        "version",
        "release",
        "tags",
        "public",
        "bookmarked",
    }

    result = {}
    for attr in safe_attrs:
        if hasattr(obj, attr):
            result[attr] = getattr(obj, attr)

    if not result:
        logger.warning(
            "Unable to serialize Langfuse object of type %s - no known serialization methods found",
            type(obj).__name__,
        )
        raise ValueError(f"Cannot serialize Langfuse object of type {type(obj).__name__}")

    return result


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

        trace_dict = _convert_langfuse_object_to_dict(trace)

        # Ensure observations and scores are serialized correctly
        if hasattr(trace, "observations") and not trace_dict.get("observations"):
            trace_dict["observations"] = [
                _convert_langfuse_object_to_dict(o) for o in trace.observations
            ]

        if hasattr(trace, "scores") and not trace_dict.get("scores"):
            trace_dict["scores"] = [_convert_langfuse_object_to_dict(s) for s in trace.scores]

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
