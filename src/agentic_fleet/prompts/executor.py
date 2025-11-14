"""Executor agent prompt template."""

from __future__ import annotations


def get_instructions() -> str:
    """Get executor agent instructions.

    Returns:
        Executor agent instructions string
    """
    return """You are the executor agent. Carry out the active instruction from the
manager or planner. Execute reasoning-heavy steps, delegate to registered tools when needed,
and produce clear artifacts or status updates. If a tool is required, call it explicitly and
then explain the outcome."""


__all__ = ["get_instructions"]
