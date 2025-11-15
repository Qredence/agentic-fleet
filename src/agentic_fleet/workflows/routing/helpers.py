"""Routing helper functions."""

from __future__ import annotations

from typing import Any

from ...utils.models import ExecutionMode, RoutingDecision, ensure_routing_decision


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

    return routing


def detect_routing_edge_cases(task: str, routing: RoutingDecision) -> list[str]:
    """
    Detect edge cases in routing decisions for logging and learning.

    Returns:
        List of detected edge case descriptions
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

    return edge_cases
