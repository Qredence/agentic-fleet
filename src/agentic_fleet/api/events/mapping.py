"""Event mapping logic for converting internal workflow events to API stream events.

This module centralizes the logic for transforming various internal workflow events
(from DSPy, Agents, or the Executor) into standardized StreamEvents for the API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

import yaml
from agent_framework._workflows import (
    ExecutorCompletedEvent,
    RequestInfoEvent,
    WorkflowOutputEvent,
    WorkflowStartedEvent,
    WorkflowStatusEvent,
)

from agentic_fleet.models import (
    EventCategory,
    StreamEvent,
    StreamEventType,
    UIHint,
)
from agentic_fleet.utils.cfg import get_config_path
from agentic_fleet.utils.logger import setup_logger
from agentic_fleet.workflows.models import (
    MagenticAgentMessageEvent,
    ReasoningStreamEvent,
)

logger = setup_logger(__name__)


# =============================================================================
# UI Routing Configuration Loading
# =============================================================================

# Type alias for priority literal
PriorityType = Literal["low", "medium", "high"]

# Valid workflow state names for WorkflowStatusEvent processing
VALID_WORKFLOW_STATES = {"FAILED", "IN_PROGRESS", "IDLE", "COMPLETED", "CANCELLED"}


class UIHintData(TypedDict):
    """Typed dict for validated UI hint data."""

    component: str
    priority: PriorityType
    collapsible: bool
    icon_hint: str | None


@dataclass(frozen=True)
class UIRoutingEntry:
    """A single UI routing entry from workflow_config.yaml.

    Represents the UI hints and category for a specific event type/kind combination.
    """

    component: str
    priority: PriorityType
    collapsible: bool
    category: str
    icon_hint: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], context: str) -> UIRoutingEntry:
        """Parse and validate a UI routing entry from raw dict.

        Args:
            data: Raw dict from YAML config.
            context: Description of config location for error messages.

        Returns:
            Validated UIRoutingEntry instance.
        """
        if not isinstance(data, dict):
            logger.warning(
                "Invalid ui_routing entry at %s (expected dict, got %s), using defaults",
                context,
                type(data).__name__,
            )
            return cls(
                component=_DEFAULT_COMPONENT,
                priority=_DEFAULT_PRIORITY,
                collapsible=_DEFAULT_COLLAPSIBLE,
                category=_DEFAULT_CATEGORY,
                icon_hint=None,
            )

        # Validate component (required string)
        component = data.get("component")
        if not (isinstance(component, str) and component):
            logger.warning(
                "Invalid/missing 'component' at %s, using default '%s'",
                context,
                _DEFAULT_COMPONENT,
            )
            component = _DEFAULT_COMPONENT

        # Validate priority (must be low/medium/high)
        priority = data.get("priority")
        if priority not in _VALID_PRIORITIES:
            if priority is not None:
                logger.warning(
                    "Invalid 'priority' value '%s' at %s, using default '%s'",
                    priority,
                    context,
                    _DEFAULT_PRIORITY,
                )
            priority = _DEFAULT_PRIORITY

        # Validate collapsible (must be bool)
        collapsible = data.get("collapsible")
        if not isinstance(collapsible, bool):
            if collapsible is not None:
                logger.warning(
                    "Invalid 'collapsible' value '%s' at %s, using default %s",
                    collapsible,
                    context,
                    _DEFAULT_COLLAPSIBLE,
                )
            collapsible = _DEFAULT_COLLAPSIBLE

        # Validate category (must be valid EventCategory)
        category_str = data.get("category", _DEFAULT_CATEGORY)
        if not isinstance(category_str, str):
            logger.warning(
                "Invalid 'category' type at %s (expected str, got %s), using default '%s'",
                context,
                type(category_str).__name__,
                _DEFAULT_CATEGORY,
            )
            category_str = _DEFAULT_CATEGORY
        else:
            category_str = category_str.lower()
            if category_str not in _VALID_CATEGORIES:
                logger.warning(
                    "Unknown 'category' value '%s' at %s, using default '%s'",
                    category_str,
                    context,
                    _DEFAULT_CATEGORY,
                )
                category_str = _DEFAULT_CATEGORY

        # Validate icon_hint (optional string or None)
        icon_hint = data.get("icon_hint")
        if icon_hint is not None and not isinstance(icon_hint, str):
            logger.warning("Invalid 'icon_hint' value '%s' at %s, using None", icon_hint, context)
            icon_hint = None

        return cls(
            component=component,
            priority=priority,  # type: ignore[arg-type]
            collapsible=collapsible,
            category=category_str,
            icon_hint=icon_hint,
        )

    def to_ui_hint_data(self) -> UIHintData:
        """Convert to UIHintData TypedDict."""
        return UIHintData(
            component=self.component,
            priority=self.priority,
            collapsible=self.collapsible,
            icon_hint=self.icon_hint,
        )

    def to_event_category(self) -> EventCategory:
        """Convert category string to EventCategory enum."""
        return EventCategory(self.category)


@dataclass
class UIRoutingEventConfig:
    """Configuration for a single event type, containing kind-specific entries."""

    entries: dict[str, UIRoutingEntry] = field(default_factory=dict)
    default_entry: UIRoutingEntry | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], event_key: str) -> UIRoutingEventConfig:
        """Parse event-level config containing kind-specific entries.

        Args:
            data: Raw dict mapping kind names to entry dicts.
            event_key: The event type key for error context.

        Returns:
            UIRoutingEventConfig with parsed entries.
        """
        if not isinstance(data, dict):
            logger.warning(
                "Invalid ui_routing.%s (expected dict, got %s), skipping",
                event_key,
                type(data).__name__,
            )
            return cls()

        entries: dict[str, UIRoutingEntry] = {}
        default_entry: UIRoutingEntry | None = None

        for kind_key, entry_data in data.items():
            context = f"ui_routing.{event_key}.{kind_key}"
            entry = UIRoutingEntry.from_dict(entry_data, context)

            if kind_key == "_default":
                default_entry = entry
            else:
                entries[kind_key] = entry

        return cls(entries=entries, default_entry=default_entry)

    def get_entry(self, kind: str | None) -> UIRoutingEntry | None:
        """Get entry for a specific kind, falling back to _default."""
        if kind and kind in self.entries:
            return self.entries[kind]
        return self.default_entry


@dataclass
class UIRoutingConfig:
    """Type-safe representation of the ui_routing section from workflow_config.yaml.

    Mirrors the YAML structure with validated entries.
    """

    event_configs: dict[str, UIRoutingEventConfig] = field(default_factory=dict)
    fallback: UIRoutingEntry | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UIRoutingConfig:
        """Parse and validate the full ui_routing config from raw dict.

        Args:
            data: Raw ui_routing dict from YAML config.

        Returns:
            Validated UIRoutingConfig instance.
        """
        if not isinstance(data, dict):
            logger.warning(
                "ui_routing section is malformed (expected dict, got %s), using defaults",
                type(data).__name__,
            )
            return cls()

        event_configs: dict[str, UIRoutingEventConfig] = {}
        fallback: UIRoutingEntry | None = None

        for key, value in data.items():
            if key == "_fallback":
                fallback = UIRoutingEntry.from_dict(value, "ui_routing._fallback")
            else:
                event_configs[key] = UIRoutingEventConfig.from_dict(value, key)

        logger.debug("Parsed UI routing config with %d event types", len(event_configs))
        return cls(event_configs=event_configs, fallback=fallback)

    def get_event_config(self, event_key: str) -> UIRoutingEventConfig | None:
        """Get config for a specific event type."""
        return self.event_configs.get(event_key)


# Default fallback values (used when config is missing or invalid)
_DEFAULT_COMPONENT = "ChatStep"
_DEFAULT_PRIORITY: PriorityType = "low"
_DEFAULT_COLLAPSIBLE = True
_DEFAULT_CATEGORY = "status"


# Valid values for validation
_VALID_PRIORITIES: set[str] = {"low", "medium", "high"}
_VALID_CATEGORIES: set[str] = {cat.value for cat in EventCategory}

# Module-level cache for UI routing config
_ui_routing_config: UIRoutingConfig | None = None


def _load_ui_routing_config() -> UIRoutingConfig:
    """Load and cache UI routing configuration from workflow_config.yaml.

    Returns:
        UIRoutingConfig instance (may be empty if loading fails).

    Raises:
        Logs errors but does not raise - returns empty UIRoutingConfig for graceful fallback.
    """
    global _ui_routing_config

    if _ui_routing_config is not None:
        return _ui_routing_config

    # Use centralized config path resolution (handles CWD and package locations)
    config_path = get_config_path("workflow_config.yaml")

    try:
        if not config_path.exists():
            logger.warning(
                "UI routing config not found at %s, using hardcoded defaults", config_path
            )
            _ui_routing_config = UIRoutingConfig()
            return _ui_routing_config

        with config_path.open("r", encoding="utf-8") as f:
            full_config = yaml.safe_load(f)

        if not isinstance(full_config, dict):
            logger.error(
                "workflow_config.yaml is malformed (expected dict, got %s), using defaults",
                type(full_config).__name__,
            )
            _ui_routing_config = UIRoutingConfig()
            return _ui_routing_config

        raw_ui_routing = full_config.get("ui_routing", {})
        _ui_routing_config = UIRoutingConfig.from_dict(raw_ui_routing)

    except yaml.YAMLError as e:
        logger.error("Failed to parse workflow_config.yaml: %s", e)
        _ui_routing_config = UIRoutingConfig()
    except OSError as e:
        logger.error("Failed to read workflow_config.yaml: %s", e)
        _ui_routing_config = UIRoutingConfig()

    return _ui_routing_config


def _get_default_entry() -> UIRoutingEntry:
    """Get the hardcoded default UIRoutingEntry."""
    return UIRoutingEntry(
        component=_DEFAULT_COMPONENT,
        priority=_DEFAULT_PRIORITY,
        collapsible=_DEFAULT_COLLAPSIBLE,
        category=_DEFAULT_CATEGORY,
        icon_hint=None,
    )


def classify_event(
    event_type: StreamEventType,
    kind: str | None = None,
) -> tuple[EventCategory, UIHint]:
    """Rule-based event classification for UI component routing.

    Maps StreamEventType and optional kind to semantic category and UI hints.
    Configuration is loaded from workflow_config.yaml under the ui_routing key.
    Falls back to sensible defaults if config is missing or invalid.

    Args:
        event_type: The stream event type.
        kind: Optional event kind hint (routing, analysis, quality, progress).

    Returns:
        Tuple of (EventCategory, UIHint) for frontend rendering.
    """
    config = _load_ui_routing_config()

    # Convert event type to config key (e.g., orchestrator.thought -> orchestrator_thought)
    # Dots are replaced with underscores to match YAML keys defined using underscores.
    event_key = event_type.value.lower().replace(".", "_")

    # Look up event type in config
    event_config = config.get_event_config(event_key)

    if event_config is None:
        # Fall back to _fallback config or hardcoded defaults
        entry = config.fallback if config.fallback else _get_default_entry()
        return entry.to_event_category(), UIHint(**entry.to_ui_hint_data())

    # Look up kind-specific config or fall back to _default
    entry = event_config.get_entry(kind)

    if entry is None:
        # No matching kind and no _default - use fallback
        entry = config.fallback if config.fallback else _get_default_entry()

    return entry.to_event_category(), UIHint(**entry.to_ui_hint_data())


def map_workflow_event(
    event: Any,
    accumulated_reasoning: str,
) -> tuple[StreamEvent | list[StreamEvent] | None, str]:
    """
    Convert an internal workflow event into one or more StreamEvent objects for SSE streaming.

    This function maps a variety of internal event shapes (reasoning deltas/completions, agent messages/outputs,
    executor phase messages, and final workflow output) to standardized StreamEvent instances used by the UI.
    It may return a single StreamEvent, a list of StreamEvent objects when multiple UI events are appropriate,
    or None when the input event should not produce any UI emission. It also returns an updated accumulated
    reasoning string used to aggregate reasoning stream content across events.

    Parameters:
        event: The workflow event to map. Supported inputs include framework event objects, dict-based events,
            and executor/message wrapper objects; the mapper performs safe extraction and duck-typing to
            recognize different event payloads.
        accumulated_reasoning: Running concatenation of reasoning text used to accumulate partial reasoning
            across ReasoningStreamEvent occurrences.

    Returns:
        A tuple where the first element is either a StreamEvent, a list of StreamEvent, or None if no event
        should be emitted, and the second element is the updated accumulated_reasoning string.
    """
    # Skip generic WorkflowStartedEvent - covered by IN_PROGRESS status event
    if isinstance(event, WorkflowStartedEvent):
        return None, accumulated_reasoning

    # Handle WorkflowStatusEvent - convert FAILED to error, IN_PROGRESS to progress status
    if isinstance(event, WorkflowStatusEvent):
        state = event.state
        data = event.data or {}
        message = data.get("message", "")
        workflow_id = data.get("workflow_id", "")

        # Convert state to a valid state name (enum or string), else skip with warning
        if hasattr(state, "name"):
            state_name = state.name
        elif isinstance(state, str):
            state_name = state.upper()
        else:
            logger.warning(
                f"Unrecognized workflow state type: {type(state)} ({state!r}) in WorkflowStatusEvent; skipping event."
            )
            return None, accumulated_reasoning

        if state_name not in VALID_WORKFLOW_STATES:
            logger.warning(
                f"Unrecognized workflow state value: {state_name!r} in WorkflowStatusEvent; skipping event."
            )
            return None, accumulated_reasoning
        if state_name == "FAILED":
            # Convert FAILED status to error event
            event_type = StreamEventType.ERROR
            category, ui_hint = classify_event(event_type)
            return (
                StreamEvent(
                    type=event_type,
                    error=message or "Workflow failed",
                    data={"workflow_id": workflow_id, **data},
                    category=category,
                    ui_hint=ui_hint,
                ),
                accumulated_reasoning,
            )
        elif state_name == "IN_PROGRESS":
            # Convert IN_PROGRESS to orchestrator message with progress kind
            event_type = StreamEventType.ORCHESTRATOR_MESSAGE
            kind = "progress"
            category, ui_hint = classify_event(event_type, kind)
            return (
                StreamEvent(
                    type=event_type,
                    message=message or "Workflow started",
                    kind=kind,
                    data={"workflow_id": workflow_id, **data},
                    category=category,
                    ui_hint=ui_hint,
                ),
                accumulated_reasoning,
            )
        # Skip IDLE and other states
        return None, accumulated_reasoning

    # Handle agent-framework workflow request events (HITL).
    # These pause workflow execution until the host sends responses keyed by request_id.
    if isinstance(event, RequestInfoEvent):
        data = getattr(event, "data", None)
        request_id = None
        request_obj = None

        if data is not None:
            request_id = getattr(data, "request_id", None)
            request_obj = getattr(data, "request", None)
            if request_id is None and isinstance(data, dict):
                request_id = data.get("request_id")
                request_obj = data.get("request")

        if request_id is None:
            # Best-effort extraction for older shapes
            request_id = getattr(event, "request_id", None)

        request_type_name = type(request_obj).__name__ if request_obj is not None else None
        if request_type_name is None and data is not None:
            request_type_name = type(data).__name__

        # Best-effort serialization of the payload for the frontend.
        payload: Any | None = None
        if request_obj is not None:
            if hasattr(request_obj, "model_dump"):
                try:
                    payload = request_obj.model_dump()
                except Exception:
                    payload = None
            elif hasattr(request_obj, "to_dict"):
                try:
                    payload = request_obj.to_dict()
                except Exception:
                    payload = None
            elif isinstance(request_obj, dict):
                payload = request_obj
            else:
                payload = {
                    "type": request_type_name,
                    "repr": repr(request_obj),
                }

        # Pick a UI message based on the request kind.
        msg = "Action required"
        lowered = (request_type_name or "").lower()
        if "approval" in lowered:
            msg = "Tool approval required"
        elif "user" in lowered and "input" in lowered:
            msg = "User input required"
        elif "intervention" in lowered or "plan" in lowered:
            msg = "Human intervention required"

        event_type = StreamEventType.ORCHESTRATOR_MESSAGE
        kind = "request"
        category, ui_hint = classify_event(event_type, kind)
        return (
            StreamEvent(
                type=event_type,
                message=msg,
                agent_id="orchestrator",
                kind=kind,
                data={
                    "request_id": request_id,
                    "request_type": request_type_name,
                    "request": payload,
                },
                category=category,
                ui_hint=ui_hint,
            ),
            accumulated_reasoning,
        )

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
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            logger.warning(
                "Failed to extract text from chat message contents: %s", exc, exc_info=True
            )
            text = ""

        if text:
            author_name = getattr(event, "author_name", None) or getattr(event, "author", None)
            role = getattr(event, "role", None)
            role_value = role.value if role is not None and hasattr(role, "value") else role

            # Emit agent messages as agent-level stream events only.
            # The authoritative final answer is emitted via WorkflowOutputEvent mapping.
            event_type = StreamEventType.AGENT_MESSAGE
            category, ui_hint = classify_event(event_type)
            return (
                StreamEvent(
                    type=event_type,
                    message=text,
                    agent_id=getattr(event, "agent_id", None),
                    author=author_name,
                    role=role_value,
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
            role_value = role.value if role is not None and hasattr(role, "value") else role
            author_name = getattr(event, "author_name", None) or getattr(event, "author", None)
            agent_id = getattr(event, "agent_id", None) or author_name

            # Emit agent messages as agent-level stream events only.
            msg_type = StreamEventType.AGENT_MESSAGE
            msg_category, msg_ui_hint = classify_event(msg_type)
            return (
                StreamEvent(
                    type=msg_type,
                    message=text,
                    agent_id=agent_id,
                    author=author_name,
                    role=role_value,
                    kind=None,
                    category=msg_category,
                    ui_hint=msg_ui_hint,
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
                elif role is not None and hasattr(role, "value"):
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
        from agentic_fleet.workflows.models import (
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
            elif not isinstance(data, list) and hasattr(data, "result"):
                result_text = str(getattr(data, "result", ""))
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
                            role=role.value
                            if role is not None and hasattr(role, "value")
                            else role,
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
