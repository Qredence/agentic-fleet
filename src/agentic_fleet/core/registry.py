"""Compatibility shim for legacy import path.

Historically `ToolRegistry` lived under `agentic_fleet.core.registry`. It
was relocated to `agentic_fleet.tools.registry` but some modules (and
external integrations/tests) still import the old path. This shim preserves
backward compatibility and can be removed in a future major release once
all imports are updated.
"""

from __future__ import annotations

from agentic_fleet.tools.registry import ToolRegistry

__all__ = ["ToolRegistry"]
