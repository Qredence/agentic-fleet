"""Routing decision helpers.

This module provides utilities for normalizing, validating, and preparing
routing decisions for the workflow execution pipeline.
"""

from __future__ import annotations

from typing import Any

from ...dspy_modules.reasoner_utils import is_time_sensitive_task
from ...utils.logger import setup_logger
from ...utils.models import ExecutionMode, RoutingDecision, ensure_routing_decision

logger = setup_logger(__name__)


def _create_routing_decision(
    routing: RoutingDecision,
    mode: ExecutionMode | None = None,
    subtasks: tuple[str, ...] | None = None,
) -> RoutingDecision:
    """Create a new RoutingDecision with updated mode and/or subtasks.

    Args:
        routing: The original routing decision
        mode: Optional new mode (defaults to routing.mode)
        subtasks: Optional new subtasks (defaults to routing.subtasks)

    Returns:
        New RoutingDecision with updated fields
    """
    return RoutingDecision(
        task=routing.task,
        assigned_to=routing.assigned_to,
        mode=mode if mode is not None else routing.mode,
        subtasks=subtasks if subtasks is not None else routing.subtasks,
        confidence=routing.confidence,
        tool_requirements=routing.tool_requirements,
    )


def normalize_routing_decision(
    routing: RoutingDecision | dict[str, Any], task: str
) -> RoutingDecision:
    """Ensure routing output has valid agents, mode, and subtasks."""
    # Convert dict to RoutingDecision if needed
    if isinstance(routing, dict):
        routing = ensure_routing_decision(routing)

    # Validate and normalize
    if not routing.assigned_to:
        # Fallback: assign to Researcher for research tasks
        routing = RoutingDecision(
            task=task,
            assigned_to=("Researcher",),
            mode=ExecutionMode.DELEGATED,
            subtasks=(),
            confidence=routing.confidence,
        )

    # Ensure mode is valid
    if routing.mode not in (
        ExecutionMode.DELEGATED,
        ExecutionMode.SEQUENTIAL,
        ExecutionMode.PARALLEL,
    ):
        routing = RoutingDecision(
            task=routing.task,
            assigned_to=routing.assigned_to,
            mode=ExecutionMode.DELEGATED,
            subtasks=routing.subtasks,
            confidence=routing.confidence,
        )

    # Normalize latency-conscious defaults:
    # - Delegated with multiple agents ⇒ parallel fan-out.
    # - Parallel with insufficient subtasks ⇒ normalize subtasks.
    # - Parallel with single agent ⇒ back to delegated.
    if routing.mode is ExecutionMode.DELEGATED and len(routing.assigned_to) > 1:
        routing = _create_routing_decision(
            routing,
            mode=ExecutionMode.PARALLEL,
            subtasks=tuple(
                prepare_subtasks(
                    list(routing.assigned_to),
                    list(routing.subtasks) if routing.subtasks is not None else None,
                    task,
                )
            ),
        )

    elif routing.mode is ExecutionMode.PARALLEL:
        if len(routing.assigned_to) <= 1:
            routing = _create_routing_decision(
                routing,
                mode=ExecutionMode.DELEGATED,
            )
        else:
            routing = _create_routing_decision(
                routing,
                mode=ExecutionMode.PARALLEL,
                subtasks=tuple(
                    prepare_subtasks(
                        list(routing.assigned_to),
                        list(routing.subtasks) if routing.subtasks is not None else None,
                        task,
                    )
                ),
            )

    return routing


def detect_routing_edge_cases(task: str, routing: RoutingDecision) -> list[str]:
    """Detect edge cases in routing decisions for logging and learning.

    Identifies potential issues or unusual patterns in routing decisions
    that may require attention or could be used for improving future routing.

    Args:
        task: The original task being routed.
        routing: The routing decision to analyze.

    Returns:
        List of detected edge case descriptions. Empty if no issues found.

    Example:
        >>> edge_cases = detect_routing_edge_cases("Find today's news", routing)
        >>> if edge_cases:
        ...     logger.warning(f"Edge cases: {edge_cases}")
    """
    edge_cases = []

    # Check for ambiguous routing
    if routing.confidence is not None and routing.confidence < 0.5:
        edge_cases.append("Low confidence routing decision")

    # Check for mismatched mode and agents
    if routing.mode == ExecutionMode.PARALLEL and len(routing.assigned_to) == 1:
        edge_cases.append("Parallel mode with single agent")

    if routing.mode == ExecutionMode.DELEGATED and len(routing.assigned_to) > 1:
        edge_cases.append("Delegated mode with multiple agents")

    # Check for empty subtasks in parallel mode
    if routing.mode == ExecutionMode.PARALLEL and not routing.subtasks:
        edge_cases.append("Parallel mode without subtasks")

    # Time-sensitive queries should include a web-search tool
    if is_time_sensitive_task(task):
        has_web_tool = bool(
            routing.tool_requirements
            and any(
                t.lower().startswith("tavily") or "search" in t.lower() or "web" in t.lower()
                for t in routing.tool_requirements
            )
        )
        if not has_web_tool:
            edge_cases.append("Time-sensitive task missing web search tool")

    return edge_cases


def prepare_subtasks(
    agents: list[str], subtasks: list[str] | None, fallback_task: str
) -> list[str]:
    """Normalize DSPy-provided subtasks to align with assigned agents.

    Ensures the number of subtasks matches the number of agents by
    either padding with the fallback task or truncating excess subtasks.

    Args:
        agents: List of agent names assigned to the task.
        subtasks: Optional list of subtasks from DSPy routing.
        fallback_task: Task to use when subtasks are missing or insufficient.

    Returns:
        List of subtasks with length equal to number of agents.
    """
    if not agents:
        return []

    normalized: list[str]
    if not subtasks:
        normalized = [fallback_task for _ in agents]
    else:
        normalized = [str(task) for task in subtasks]

    if len(normalized) < len(agents):
        normalized.extend([fallback_task] * (len(agents) - len(normalized)))
    elif len(normalized) > len(agents):
        normalized = normalized[: len(agents)]

    return normalized
