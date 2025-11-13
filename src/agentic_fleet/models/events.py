"""Workflow event models."""

from collections.abc import AsyncGenerator
from typing import Any, NotRequired, TypedDict

from agentic_fleet.models.requests import WorkflowRunRequest


class WorkflowEvent(TypedDict, total=True):
    """Workflow event structure for SSE streaming.

    The ``type`` and ``data`` keys are treated as required to simplify static
    analysis in tests that index directly into ``event['type']`` and
    ``event['data']``. Optional OpenAI-specific fields remain ``NotRequired``.
    """

    type: str
    data: dict[str, Any]
    openai_type: NotRequired[str]  # For OpenAI-compatible format
    correlation_id: NotRequired[str]  # For request tracing


class RunsWorkflow:
    """Protocol for workflows that can run and stream events.

    Backward compatibility: earlier versions accepted ``message: str`` while
    newer surfaces pass a ``WorkflowRunRequest`` to allow richer metadata. We
    support both via a union parameter.
    """

    async def run(self, request: WorkflowRunRequest | str) -> AsyncGenerator[WorkflowEvent, None]:
        """Run workflow and stream events.

        Concrete implementations should normalize ``request`` internally.
        """
        if False:  # pragma: no cover - protocol stub
            yield
        raise NotImplementedError
