"""Backbone participant creation for the dynamic workflow."""

from __future__ import annotations

from collections.abc import Mapping

from agent_framework import AgentProtocol

from .executor import create_executor_participant
from .generator import create_generator_participant
from .planner import create_planner_participant
from .verifier import create_verifier_participant


def create_backbone_participants(
    *,
    model: str | None = None,
) -> Mapping[str, AgentProtocol]:
    """Instantiate the planner, executor, verifier, and generator modules."""
    return {
        "planner": create_planner_participant(model=model),
        "executor": create_executor_participant(model=model),
        "verifier": create_verifier_participant(model=model),
        "generator": create_generator_participant(model=model),
    }


__all__ = ["create_backbone_participants"]
