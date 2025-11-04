"""Service layer for workflows API."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv not available, rely on system/env vars

from agentic_fleet.models.events import RunsWorkflow, WorkflowEvent
from agentic_fleet.utils.logging_sanitize import sanitize_log_value

DEFAULT_WORKFLOW_ID = "magentic_fleet"

logger = logging.getLogger(__name__)


class StubMagenticFleetWorkflow(RunsWorkflow):
    """Deterministic stub workflow used in tests and fallback scenarios.

    Parameters:
        max_delta_length: Truncation length for the delta content.
        include_agent_events: Whether to emit per-agent completion events.

    Behavioral contract:
    - Synchronous legacy factory (``create_magentic_fleet_workflow``) expects ONLY
      two events: ``message.delta`` then ``message.done``.
    - Asynchronous factory (``create_workflow``) used by chat streaming emits
      ``message.delta`` + optional ``agent.message.complete`` + ``message.done`` so
      segmented streaming tests can assert agent-level events.
    """

    def __init__(self, max_delta_length: int = 16, *, include_agent_events: bool = True):
        self.max_delta_length = max_delta_length
        self.include_agent_events = include_agent_events

    async def run(self, message: str) -> AsyncGenerator[WorkflowEvent, None]:
        truncated = message[: self.max_delta_length]

        # Always emit a message.delta (with agent_id to enable optional agent.delta SSE events)
        yield {
            "type": "message.delta",
            "data": {
                "delta": truncated,
                "agent_id": "stub-agent",
                "stub": True,
            },
        }

        # Emit agent completion event only when enabled (segmented streaming path)
        if self.include_agent_events:
            yield {
                "type": "agent.message.complete",
                "data": {
                    "agent_id": "stub-agent",
                    "content": truncated,
                    "stub": True,
                },
            }

        # Terminal done event
        yield {
            "type": "message.done",
            "data": {
                "stub": True,
            },
        }


TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _should_force_stub() -> bool:
    """Determine if the stub workflow should be forced."""

    force_stub = os.getenv("AF_FORCE_STUB_WORKFLOW")
    if force_stub is not None:
        return force_stub.strip().lower() in TRUTHY_VALUES

    # During pytest runs we default to the stub for determinism unless explicitly allowed.
    return bool(
        os.getenv("PYTEST_CURRENT_TEST")
        and os.getenv("AF_ALLOW_REAL_WORKFLOW_IN_TESTS", "").strip().lower() not in TRUTHY_VALUES
    )


async def create_workflow(
    workflow_id: str = DEFAULT_WORKFLOW_ID, *, max_delta_length: int = 16
) -> RunsWorkflow:
    """Generic workflow factory with fallback semantics.

    The function attempts to construct the requested *workflow_id*. If the
    identifier is unknown or creation fails, a stub workflow is returned (or
    the default workflow when possible) and a warning/error is logged.

    Args:
        workflow_id: Desired workflow identifier (defaults to magentic_fleet)
        max_delta_length: Truncation length for stub fallback implementation.

    Returns:
        Concrete workflow instance implementing ``RunsWorkflow``.
    """
    # Forced stub (pytest determinism or explicit override)
    if _should_force_stub():
        logger.info("Forcing stub workflow (test or override mode)")
        return StubMagenticFleetWorkflow(
            max_delta_length=max_delta_length, include_agent_events=True
        )

    if not os.getenv("OPENAI_API_KEY"):
        logger.info("OPENAI_API_KEY not set, using stub workflow")
        return StubMagenticFleetWorkflow(
            max_delta_length=max_delta_length, include_agent_events=True
        )

    try:
        from agentic_fleet.utils.factory import WorkflowFactory

        factory = WorkflowFactory()
        workflow = await factory.create_from_yaml_async(workflow_id)
        logger.info(
            "Created workflow '%s' from YAML configuration",
            sanitize_log_value(workflow_id),
        )
        return workflow
    except Exception as exc:  # Broad catch to ensure graceful fallback
        logger.error(
            "Failed to create workflow '%s': %s - falling back to stub",
            sanitize_log_value(workflow_id),
            exc,
            exc_info=True,
        )
        return StubMagenticFleetWorkflow(
            max_delta_length=max_delta_length, include_agent_events=True
        )


def create_magentic_fleet_workflow(
    max_delta_length: int = 16,
) -> RunsWorkflow:  # pragma: no cover - legacy sync alias
    """Synchronous backward-compatible factory returning a minimal stub.

    Legacy tests invoke this without ``await`` and expect ONLY two events
    (delta + done). We therefore disable per-agent completion events here.
    """
    import warnings

    warnings.warn(
        "create_magentic_fleet_workflow is deprecated; use create_workflow(workflow_id=...)",
        DeprecationWarning,
        stacklevel=2,
    )
    return StubMagenticFleetWorkflow(max_delta_length=max_delta_length, include_agent_events=False)


# Explicit re-exports for downstream modules performing attribute lookups on this service module.
__all__ = [
    "RunsWorkflow",
    "StubMagenticFleetWorkflow",
    "WorkflowEvent",
    "create_magentic_fleet_workflow",
    "create_workflow",
]
