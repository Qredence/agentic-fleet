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

DEFAULT_WORKFLOW_ID = "magentic_fleet"

logger = logging.getLogger(__name__)


class StubMagenticFleetWorkflow(RunsWorkflow):
    """Stub implementation for MagenticFleetWorkflow.

    This class does not perform any real workflow processing.
    The magic number for truncating the message is configurable via `max_delta_length`.
    API responses are marked to indicate stub behavior.
    """

    def __init__(self, max_delta_length: int = 16):
        self.max_delta_length = max_delta_length

    async def run(self, message: str) -> AsyncGenerator[WorkflowEvent, None]:
        # STUB: This implementation only returns the first `max_delta_length` characters of the message.
        # No actual workflow processing is performed.
        yield {
            "type": "message.delta",
            "data": {
                "delta": message[: self.max_delta_length],
                "agent_id": "stub-agent",
                "stub": True,
                "note": "Stub implementation: no real workflow processing performed.",
            },
        }
        # Emit an agent completion event to exercise segmented streaming logic in tests
        yield {
            "type": "agent.message.complete",
            "data": {
                "agent_id": "stub-agent",
                "content": message[: self.max_delta_length],
                "stub": True,
                "note": "Stub agent completion event for segmented streaming tests.",
            },
        }
        yield {
            "type": "message.done",
            "data": {
                "stub": True,
                "note": "Stub implementation: no real workflow processing performed.",
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
        return StubMagenticFleetWorkflow(max_delta_length=max_delta_length)

    if not os.getenv("OPENAI_API_KEY"):
        logger.info("OPENAI_API_KEY not set, using stub workflow")
        return StubMagenticFleetWorkflow(max_delta_length=max_delta_length)

    try:
        from agentic_fleet.utils.factory import WorkflowFactory

        factory = WorkflowFactory()
        workflow = await factory.create_from_yaml_async(workflow_id)
        logger.info("Created workflow '%s' from YAML configuration", workflow_id)
        return workflow
    except Exception as exc:  # Broad catch to ensure graceful fallback
        logger.error(
            "Failed to create workflow '%s': %s - falling back to stub",
            workflow_id,
            exc,
            exc_info=True,
        )
        return StubMagenticFleetWorkflow(max_delta_length=max_delta_length)


async def create_magentic_fleet_workflow(max_delta_length: int = 16) -> RunsWorkflow:
    """Deprecated alias; prefer :func:`create_workflow` with *workflow_id* parameter."""
    import warnings

    warnings.warn(
        "create_magentic_fleet_workflow is deprecated; use create_workflow(workflow_id=...)",
        DeprecationWarning,
        stacklevel=2,
    )
    return await create_workflow(DEFAULT_WORKFLOW_ID, max_delta_length=max_delta_length)
