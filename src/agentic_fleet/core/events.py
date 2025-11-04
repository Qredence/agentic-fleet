"""Backward compatibility alias - use workflow.events instead."""

from __future__ import annotations

from agentic_fleet.workflow.events import WorkflowEventBridge

__all__ = ["WorkflowEventBridge"]
