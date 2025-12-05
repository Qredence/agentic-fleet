"""Event mapping logic for converting internal workflow events to API stream events.

This module centralizes the logic for transforming various internal workflow events
(from DSPy, Agents, or the Executor) into standardized StreamEvents for the API.
"""

from __future__ import annotations

from typing import Any

from agent_framework._workflows import (
    ExecutorCompletedEvent,
    WorkflowOutputEvent,
    WorkflowStartedEvent,
    WorkflowStatusEvent,
)

from agentic_fleet.app.schemas import (
    EventCategory,
    StreamEvent,
    StreamEventType,
    UIHint,
)
from agentic_fleet.utils.logger import setup_logger
from agentic_fleet.workflows.execution.streaming_events import (
    MagenticAgentMessageEvent,
    ReasoningStreamEvent,
)

logger = setup_logger(__name__)


def classify_event(
    event_type: StreamEventType,
    kind: str | None = None,
) -> tuple[EventCategory, UIHint]:
    """Rule-based event classification for UI component routing.

    Maps StreamEventType and optional kind to semantic category and UI hints.
    This enables the frontend to route events to appropriate components.

    Args:
        event_type: The stream event type.
        kind: Optional event kind hint (routing, analysis, quality, progress).

    Returns:
        Tuple of (EventCategory, UIHint) for frontend rendering.
    """
    # Orchestrator thought events - categorize by kind
    if event_type == StreamEventType.ORCHESTRATOR_THOUGHT:
        if kind == "routing":
            return EventCategory.PLANNING, UIHint(
                component="ChatStep", priority="high", collapsible=True, icon_hint="routing"
            )
        if kind == "analysis":
            return EventCategory.THOUGHT, UIHint(
                component="ChatStep", priority="medium", collapsible=True, icon_hint="analysis"
            )
        if kind == "quality":
            return EventCategory.OUTPUT, UIHint(
                component="ChatStep", priority="medium", collapsible=True, icon_hint="quality"
            )
        if kind == "progress":
            return EventCategory.STATUS, UIHint(
                component="ChatStep", priority="low", collapsible=True, icon_hint="progress"
            )
        if kind == "handoff":
            return EventCategory.PLANNING, UIHint(
                component="ChatStep", priority="high", collapsible=False, icon_hint="handoff"
            )
        # Default thought
        return EventCategory.THOUGHT, UIHint(
            component="ChatStep", priority="medium", collapsible=True
        )

    # Orchestrator message events - status updates
    if event_type == StreamEventType.ORCHESTRATOR_MESSAGE:
        return EventCategory.STATUS, UIHint(component="ChatStep", priority="low", collapsible=True)

    # Agent lifecycle events
    if event_type == StreamEventType.AGENT_START:
        return EventCategory.STEP, UIHint(
            component="ChatStep", priority="low", collapsible=True, icon_hint="agent_start"
        )
    if event_type == StreamEventType.AGENT_COMPLETE:
        return EventCategory.STEP, UIHint(
            component="ChatStep", priority="low", collapsible=True, icon_hint="agent_complete"
        )
    if event_type == StreamEventType.AGENT_MESSAGE:
        return EventCategory.OUTPUT, UIHint(
            component="MessageBubble", priority="medium", collapsible=False
        )
    if event_type == StreamEventType.AGENT_OUTPUT:
        return EventCategory.OUTPUT, UIHint(
            component="MessageBubble", priority="high", collapsible=False
        )

    # Reasoning events (GPT-5 chain-of-thought)
    if event_type == StreamEventType.REASONING_DELTA:
        return EventCategory.REASONING, UIHint(
            component="Reasoning", priority="medium", collapsible=True
        )
    if event_type == StreamEventType.REASONING_COMPLETED:
        return EventCategory.REASONING, UIHint(
            component="Reasoning", priority="medium", collapsible=True
        )

    # Response events
    if event_type == StreamEventType.RESPONSE_DELTA:
        return EventCategory.RESPONSE, UIHint(
            component="MessageBubble", priority="high", collapsible=False
        )
    if event_type == StreamEventType.RESPONSE_COMPLETED:
        return EventCategory.RESPONSE, UIHint(
            component="MessageBubble", priority="high", collapsible=False
        )

    # Error events
    if event_type == StreamEventType.ERROR:
        return EventCategory.ERROR, UIHint(
            component="ErrorStep", priority="high", collapsible=False
        )

    if event_type == StreamEventType.CANCELLED:
        return EventCategory.STATUS, UIHint(
            component="ChatStep", priority="medium", collapsible=False, icon_hint="cancelled"
        )

    if event_type == StreamEventType.CONNECTED:
        return EventCategory.STATUS, UIHint(
            component="ChatStep", priority="low", collapsible=False, icon_hint="connected"
        )

    if event_type == StreamEventType.HEARTBEAT:
        return EventCategory.STATUS, UIHint(
            component="ChatStep", priority="low", collapsible=True, icon_hint="heartbeat"
        )

    # Control events (done) - no UI representation needed
    if event_type == StreamEventType.DONE:
        return EventCategory.STATUS, UIHint(component="ChatStep", priority="low", collapsible=True)

    # Fallback
    return EventCategory.STATUS, UIHint(component="ChatStep", priority="low", collapsible=True)


def map_workflow_event(
    event: Any,
    accumulated_reasoning: str,
) -> tuple[StreamEvent | list[StreamEvent] | None, str]:
    """Map a workflow event to a StreamEvent for SSE.

    Args:
        event: The workflow event to map.
        accumulated_reasoning: Running total of reasoning text for partial error handling.

    Returns:
        Tuple of (StreamEvent or None, updated accumulated_reasoning).
    """
    # Skip generic WorkflowStartedEvent and WorkflowStatusEvent - they provide no useful info
    # The frontend will show "Processing..." shimmer during streaming instead
    if isinstance(event, WorkflowStartedEvent):
        return None, accumulated_reasoning

    if isinstance(event, WorkflowStatusEvent):
        return None, accumulated_reasoning

    if isinstance(event, ReasoningStreamEvent):
        # GPT-5 reasoning token
        new_accumulated = accumulated_reasoning + event.reasoning
        if event.is_complete:
            event_type = StreamEventType.REASONING_COMPLETED
            category, ui_hint = classify_event(event_type)
            return (
                StreamEvent(
                    type=event_type,
                    reasoning=event.reasoning,
                    agent_id=event.agent_id,
                    category=category,
                    ui_hint=ui_hint,
                ),
                new_accumulated,
            )
        event_type = StreamEventType.REASONING_DELTA
        category, ui_hint = classify_event(event_type)
        return (
            StreamEvent(
                type=event_type,
                reasoning=event.reasoning,
                agent_id=event.agent_id,
                category=category,
                ui_hint=ui_hint,
            ),
            new_accumulated,
        )

    if isinstance(event, MagenticAgentMessageEvent):
        # Agent-level message (could be streaming or final). Surface explicitly so the frontend
        # can render per-agent thoughts/output instead of concatenated deltas.
        text = ""
        if hasattr(event, "message") and event.message:
            text = getattr(event.message, "text", "") or ""

        if not text:
            return None, accumulated_reasoning

        # Check for metadata to determine event kind/stage
        kind = None
        if hasattr(event, "stage"):
            kind = getattr(event, "stage", None)

        # Map the internal event type to the StreamEventType
        event_type = StreamEventType.AGENT_MESSAGE
        event_name = None
        if hasattr(event, "event"):
            event_name = getattr(event, "event", None)
            if event_name == "agent.start":
                event_type = StreamEventType.AGENT_START
            elif event_name == "agent.output":
                event_type = StreamEventType.AGENT_OUTPUT
            elif event_name == "agent.complete" or event_name == "agent.completed":
                event_type = StreamEventType.AGENT_COMPLETE
            elif event_name == "handoff.created":
                # Handoff events should be surfaced as orchestrator thoughts
                event_type = StreamEventType.ORCHESTRATOR_THOUGHT
                kind = "handoff"  # Override kind for handoff events

        # Get author name - prefer message.author_name, fall back to agent_id
        author_name = None
        if hasattr(event, "message") and hasattr(event.message, "author_name"):
            author_name = getattr(event.message, "author_name", None)
        if not author_name:
            author_name = event.agent_id

        # Extract payload data for rich events (handoffs, tool calls, etc.)
        event_data = None
        if hasattr(event, "payload"):
            payload = getattr(event, "payload", None)
            if payload and isinstance(payload, dict):
                event_data = payload

        # Classify the event for UI routing
        category, ui_hint = classify_event(event_type, kind)

        return (
            StreamEvent(
                type=event_type,
                message=text,
                agent_id=event.agent_id,
                kind=kind,
                author=author_name,
                role="assistant",
                category=category,
                ui_hint=ui_hint,
                data=event_data,
            ),
            accumulated_reasoning,
        )

    # Generic chat message events (agent_framework chat_message objects)
    if hasattr(event, "role") and hasattr(event, "contents"):
        try:
            # event.contents is likely a list of dicts with type/text
            text_parts = []
            for c in getattr(event, "contents", []):
                if isinstance(c, dict):
                    text_parts.append(c.get("text", ""))
                elif hasattr(c, "text"):
                    text_parts.append(getattr(c, "text", ""))
            text = "\n".join(t for t in text_parts if t)
        except Exception:
            text = ""

        if text:
            author_name = getattr(event, "author_name", None) or getattr(event, "author", None)
            role = getattr(event, "role", None)
            event_type = StreamEventType.AGENT_MESSAGE
            category, ui_hint = classify_event(event_type)
            return (
                StreamEvent(
                    type=event_type,
                    message=text,
                    agent_id=getattr(event, "agent_id", None),
                    author=author_name,
                    role=role.value if hasattr(role, "value") else role,
                    kind=None,
                    category=category,
                    ui_hint=ui_hint,
                ),
                accumulated_reasoning,
            )

    # ChatMessage-like objects with .text and .role (agent_framework ChatMessage)
    if hasattr(event, "text") and hasattr(event, "role"):
        text = getattr(event, "text", "") or ""
        if text:
            role = getattr(event, "role", None)
            author_name = getattr(event, "author_name", None) or getattr(event, "author", None)
            agent_id = getattr(event, "agent_id", None) or author_name
            event_type = StreamEventType.AGENT_MESSAGE
            category, ui_hint = classify_event(event_type)
            return (
                StreamEvent(
                    type=event_type,
                    message=text,
                    agent_id=agent_id,
                    author=author_name,
                    role=role.value if hasattr(role, "value") else role,
                    kind=None,
                    category=category,
                    ui_hint=ui_hint,
                ),
                accumulated_reasoning,
            )

    # Dict-based chat_message events (not objects)
    if isinstance(event, dict):
        event_dict: dict[str, Any] = event  # type: ignore
        if event_dict.get("type") == "chat_message":
            contents = event_dict.get("contents", [])
            text_parts: list[str] = []
            for c in contents:
                if isinstance(c, dict):
                    text_parts.append(c.get("text", ""))
                elif isinstance(c, str):
                    text_parts.append(c)
            text = "\n".join(t for t in text_parts if t)
            if text:
                author_name = event_dict.get("author_name") or event_dict.get("author")
                role = event_dict.get("role")

                # Handle role extraction safely
                role_value = role
                if isinstance(role, dict):
                    role_value = role.get("value")
                elif hasattr(role, "value"):
                    role_value = role.value

                # Determine event type
                event_type = StreamEventType.AGENT_MESSAGE
                if event_dict.get("event") == "agent.output":
                    event_type = StreamEventType.AGENT_OUTPUT

                category, ui_hint = classify_event(event_type)
                return (
                    StreamEvent(
                        type=event_type,
                        message=text,
                        agent_id=event_dict.get("agent_id") or author_name,
                        author=author_name,
                        role=role_value,
                        kind=None,
                        category=category,
                        ui_hint=ui_hint,
                    ),
                    accumulated_reasoning,
                )

    if isinstance(event, ExecutorCompletedEvent):
        # Phase completion events with typed messages
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
        from agentic_fleet.workflows.messages import (
            AnalysisMessage,
            ProgressMessage,
            QualityMessage,
            RoutingMessage,
        )

        # Use duck-typing as primary check since isinstance may fail due to module path differences
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
                        "intent": intent_data.get("intent") if intent_data else None,
                        "intent_confidence": intent_data.get("confidence") if intent_data else None,
                    },
                    category=category,
                    ui_hint=ui_hint,
                ),
                accumulated_reasoning,
            )

        if isinstance(data, RoutingMessage) or is_routing_duck:
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

        if isinstance(data, QualityMessage) or is_quality_duck:
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

        if isinstance(data, ProgressMessage) or is_progress_duck:
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

        # Skip generic phase completion - not useful for UI
        # Only emit events we can properly categorize
        return None, accumulated_reasoning

    if isinstance(event, WorkflowOutputEvent):
        # Final output event
        result_text = ""
        data = getattr(event, "data", None)

        # AgentRunResponse compatibility (framework 1.0+): unwrap messages and structured output
        structured_output = None
        messages: list[Any] = []

        if data is not None:
            if hasattr(data, "messages"):
                messages = list(getattr(data, "messages", []) or [])
                structured_output = getattr(data, "structured_output", None) or getattr(
                    data, "additional_properties", {}
                ).get("structured_output")
            elif isinstance(data, list):
                messages = data

            if messages:
                last_msg = messages[-1]
                result_text = getattr(last_msg, "text", str(last_msg)) or str(last_msg)
            elif hasattr(data, "result"):
                result_text = str(data.result)
            else:
                result_text = str(data)

        events: list[StreamEvent] = []

        if messages:
            for msg in messages:
                text = getattr(msg, "text", None) or getattr(msg, "content", "") or ""
                role = getattr(msg, "role", None)
                author = getattr(msg, "author_name", None) or getattr(msg, "author", None)
                agent_id = getattr(msg, "author", None)
                if text:
                    msg_event_type = StreamEventType.AGENT_MESSAGE
                    msg_category, msg_ui_hint = classify_event(msg_event_type)
                    events.append(
                        StreamEvent(
                            type=msg_event_type,
                            message=text,
                            agent_id=agent_id,
                            author=author,
                            role=role.value if hasattr(role, "value") else role,
                            category=msg_category,
                            ui_hint=msg_ui_hint,
                        )
                    )

        # Always push a final completion event
        final_event_type = StreamEventType.RESPONSE_COMPLETED
        final_category, final_ui_hint = classify_event(final_event_type)
        events.append(
            StreamEvent(
                type=final_event_type,
                message=result_text,
                data={"structured_output": structured_output} if structured_output else None,
                category=final_category,
                ui_hint=final_ui_hint,
            )
        )

        return events, accumulated_reasoning

    # Unknown event type - skip
    logger.debug(f"Unknown event type skipped: {type(event).__name__}")
    return None, accumulated_reasoning
