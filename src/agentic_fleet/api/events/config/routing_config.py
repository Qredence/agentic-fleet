"""UI routing configuration loading and parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

import yaml

from agentic_fleet.models import EventCategory, UIHint
from agentic_fleet.models.base import StreamEventType
from agentic_fleet.utils.cfg import get_config_path
from agentic_fleet.utils.infra.logging import setup_logger

logger = setup_logger(__name__)

# Type alias for priority literal
PriorityType = Literal["low", "medium", "high"]

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


def _get_default_entry() -> UIRoutingEntry:
    """Get the hardcoded default UIRoutingEntry."""
    return UIRoutingEntry(
        component=_DEFAULT_COMPONENT,
        priority=_DEFAULT_PRIORITY,
        collapsible=_DEFAULT_COLLAPSIBLE,
        category=_DEFAULT_CATEGORY,
        icon_hint=None,
    )


def load_ui_routing_config() -> UIRoutingConfig:
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
    config = load_ui_routing_config()

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
