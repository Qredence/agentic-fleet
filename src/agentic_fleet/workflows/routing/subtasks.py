"""Subtask preparation utilities."""

from __future__ import annotations


def prepare_subtasks(
    agents: list[str], subtasks: list[str] | None, fallback_task: str
) -> list[str]:
    """Normalize DSPy-provided subtasks to align with assigned agents."""
    if not agents:
        return []

    normalized: list[str]
    if not subtasks:
        normalized = [fallback_task for _ in agents]
    else:
        normalized = [str(task) for task in subtasks]

    if len(normalized) < len(agents):
        normalized.extend([fallback_task] * (len(agents) - len(normalized)))
    elif len(normalized) > len(agents):
        normalized = normalized[: len(agents)]

    return normalized
