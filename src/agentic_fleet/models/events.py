"""Workflow event models."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any, NotRequired, TypedDict


class WorkflowEvent(TypedDict, total=False):
    """Workflow event structure for SSE streaming."""

    type: str
    data: NotRequired[dict[str, Any]]
    openai_type: NotRequired[str]  # For OpenAI-compatible format
    correlation_id: NotRequired[str]  # For request tracing


class RunsWorkflow:
    """Protocol for workflows that can run and stream events."""

    async def run(self, message: str) -> AsyncGenerator[WorkflowEvent, None]:
        """Run workflow and stream events."""
        if False:  # pragma: no cover
            yield
        raise NotImplementedError
