"""Event mapping logic for converting internal workflow events to API stream events.

This module centralizes the logic for transforming various internal workflow events
(from DSPy, Agents, or the Executor) into standardized StreamEvents for the API.

The module has been refactored to use a modular architecture:
- config/: UI routing configuration loading and parsing
- handlers/: Event handler functions organized by event type
- dispatch.py: Event dispatch factory for O(1) event type lookup
"""

from __future__ import annotations

from agentic_fleet.api.events.config.routing_config import classify_event
from agentic_fleet.api.events.dispatch import map_workflow_event

__all__ = ["classify_event", "map_workflow_event"]
