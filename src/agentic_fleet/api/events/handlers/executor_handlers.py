"""Handlers for executor completion events (analysis, routing, quality, progress)."""

from __future__ import annotations

from typing import Any

from agent_framework._workflows import ExecutorCompletedEvent

from agentic_fleet.api.events.config.routing_config import classify_event
from agentic_fleet.models import StreamEvent
from agentic_fleet.models.base import StreamEventType
from agentic_fleet.utils.infra.logging import setup_logger

logger = setup_logger(__name__)


def handle_executor_completed(
    event: ExecutorCompletedEvent, accumulated_reasoning: str
) -> tuple[StreamEvent | None, str]:
    """Handle phase completion events with typed messages."""
    data = getattr(event, "data", None)
    if data is None:
        logger.warning(f"ExecutorCompletedEvent received without data: {event}")
        return None, accumulated_reasoning

    # agent_framework wraps executor output in a list - unwrap it
    if isinstance(data, list):
        if len(data) == 0:
            return None, accumulated_reasoning
        data = data[0]  # Get the actual message from the list

    # Map different phase message types to thoughts
    # Local imports to avoid circular dependency
    from agentic_fleet.workflows.models import (
        AnalysisMessage,
        ProgressMessage,
        QualityMessage,
        RoutingMessage,
    )

    # Use duck-typing as primary check
    is_analysis_duck = hasattr(data, "analysis") and hasattr(data, "task")
    is_routing_duck = hasattr(data, "routing") and hasattr(data, "task")
    is_quality_duck = hasattr(data, "quality") and hasattr(data, "result")
    is_progress_duck = hasattr(data, "progress") and hasattr(data, "result")

    # Log for debugging
    logger.debug(
        f"ExecutorCompletedEvent: type={type(data).__name__}, "
        f"analysis={is_analysis_duck}, routing={is_routing_duck}"
    )

    if isinstance(data, AnalysisMessage) or is_analysis_duck:
        return handle_analysis_message(data, accumulated_reasoning)

    if isinstance(data, RoutingMessage) or is_routing_duck:
        return handle_routing_message(data, accumulated_reasoning)

    if isinstance(data, QualityMessage) or is_quality_duck:
        return handle_quality_message(data, accumulated_reasoning)

    if isinstance(data, ProgressMessage) or is_progress_duck:
        return handle_progress_message(data, accumulated_reasoning)

    # Skip generic phase completion - not useful for UI
    return None, accumulated_reasoning


def handle_analysis_message(
    data: Any, accumulated_reasoning: str
) -> tuple[StreamEvent | None, str]:
    """Handle AnalysisMessage events."""
    # Defensive check: ensure data.analysis is present before accessing its attributes
    if not getattr(data, "analysis", None):
        return None, accumulated_reasoning

    event_type = StreamEventType.ORCHESTRATOR_THOUGHT
    kind = "analysis"
    category, ui_hint = classify_event(event_type, kind)
    capabilities = list(data.analysis.capabilities) if data.analysis.capabilities else []
    # Build a descriptive message based on analysis
    caps_str = ", ".join(capabilities[:3]) if capabilities else "general reasoning"
    message = f"Task requires {caps_str} ({data.analysis.complexity} complexity)"
    # Include reasoning from DSPy if available
    reasoning = data.metadata.get("reasoning", "") if data.metadata else ""
    intent_data = data.metadata.get("intent") if data.metadata else None

    # Handle intent_data: can be a string (intent name) or dict (intent + confidence)
    if isinstance(intent_data, dict):
        intent_name = intent_data.get("intent")
        intent_confidence = intent_data.get("confidence")
    elif isinstance(intent_data, str):
        # Legacy format: intent is stored as a string
        intent_name = intent_data
        intent_confidence = data.metadata.get("intent_confidence") if data.metadata else None
    else:
        intent_name = None
        intent_confidence = None

    return (
        StreamEvent(
            type=event_type,
            message=message,
            agent_id="orchestrator",
            kind=kind,
            data={
                "complexity": data.analysis.complexity,
                "capabilities": capabilities,
                "steps": data.analysis.steps,
                "reasoning": reasoning,
                "intent": intent_name,
                "intent_confidence": intent_confidence,
            },
            category=category,
            ui_hint=ui_hint,
        ),
        accumulated_reasoning,
    )


def handle_routing_message(data: Any, accumulated_reasoning: str) -> tuple[StreamEvent | None, str]:
    """Handle RoutingMessage events."""
    event_type = StreamEventType.ORCHESTRATOR_THOUGHT
    kind = "routing"
    category, ui_hint = classify_event(event_type, kind)
    routing_data = getattr(data, "routing", None)
    decision = getattr(routing_data, "decision", routing_data) if routing_data else None
    if decision is None:
        return None, accumulated_reasoning
    agents = list(decision.assigned_to) if decision.assigned_to else []
    subtasks = list(decision.subtasks) if decision.subtasks else []
    # Build descriptive message
    agents_str = " → ".join(agents) if agents else "default"
    message = f"Routing to {agents_str} ({decision.mode.value} mode)"
    if subtasks:
        message += f" with {len(subtasks)} subtask(s)"
    # Get reasoning from metadata or routing plan
    reasoning = data.metadata.get("reasoning", "") if data.metadata else ""
    return (
        StreamEvent(
            type=event_type,
            message=message,
            agent_id="orchestrator",
            kind=kind,
            data={
                "mode": decision.mode.value,
                "assigned_to": agents,
                "subtasks": subtasks,
                "reasoning": reasoning,
            },
            category=category,
            ui_hint=ui_hint,
        ),
        accumulated_reasoning,
    )


def handle_quality_message(data: Any, accumulated_reasoning: str) -> tuple[StreamEvent | None, str]:
    """Handle QualityMessage events."""
    event_type = StreamEventType.ORCHESTRATOR_THOUGHT
    kind = "quality"
    category, ui_hint = classify_event(event_type, kind)
    quality_data = getattr(data, "quality", None)
    if quality_data is None:
        return None, accumulated_reasoning
    missing = list(getattr(quality_data, "missing", []) or [])
    improvements = list(getattr(quality_data, "improvements", []) or [])
    score = getattr(quality_data, "score", 0.0)
    return (
        StreamEvent(
            type=event_type,
            message=f"Quality assessment: score {score:.1f}/10",
            agent_id="orchestrator",
            kind=kind,
            data={
                "score": score,
                "missing": missing,
                "improvements": improvements,
            },
            category=category,
            ui_hint=ui_hint,
        ),
        accumulated_reasoning,
    )


def handle_progress_message(
    data: Any, accumulated_reasoning: str
) -> tuple[StreamEvent | None, str]:
    """Handle ProgressMessage events."""
    event_type = StreamEventType.ORCHESTRATOR_MESSAGE
    kind = "progress"
    category, ui_hint = classify_event(event_type, kind)
    progress_data = getattr(data, "progress", None)
    if progress_data is None:
        return None, accumulated_reasoning
    action = getattr(progress_data, "action", "processing")
    feedback = getattr(progress_data, "feedback", "")
    return (
        StreamEvent(
            type=event_type,
            message=f"Progress: {action}",
            agent_id="orchestrator",
            kind=kind,
            data={"action": action, "feedback": feedback},
            category=category,
            ui_hint=ui_hint,
        ),
        accumulated_reasoning,
    )
