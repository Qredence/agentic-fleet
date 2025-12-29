"""Event handler functions for mapping workflow events to stream events."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agentic_fleet.models import StreamEvent

# Type alias for handler signature
EventHandler = Callable[[Any, str], tuple[StreamEvent | list[StreamEvent] | None, str]]

__all__ = ["EventHandler"]
