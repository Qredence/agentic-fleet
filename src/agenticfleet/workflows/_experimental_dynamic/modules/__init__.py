"""Module helpers for the dynamic workflow."""

from agent_framework import AgentProtocol

from .backbone import create_backbone_participants
from .executor import create_executor_participant
from .generator import create_generator_participant
from .participants import (
    DynamicWorkflowParticipants,
    create_default_dynamic_participants,
)
from .planner import create_planner_participant
from .verifier import create_verifier_participant

# Convenience aliases expected by some callers/tests


def create_planner_agent(
    *, name: str = "planner", instructions: str | None = None, model: str | None = None
) -> AgentProtocol:
    return create_planner_participant(name=name, instructions=instructions, model=model)


def create_executor_agent(
    *, name: str = "executor", instructions: str | None = None, model: str | None = None
) -> AgentProtocol:
    return create_executor_participant(name=name, instructions=instructions, model=model)


def create_verifier_agent(
    *, name: str = "verifier", instructions: str | None = None, model: str | None = None
) -> AgentProtocol:
    return create_verifier_participant(name=name, instructions=instructions, model=model)


def create_generator_agent(
    *, name: str = "generator", instructions: str | None = None, model: str | None = None
) -> AgentProtocol:
    return create_generator_participant(name=name, instructions=instructions, model=model)


__all__ = [
    "create_backbone_participants",
    "create_planner_participant",
    "create_executor_participant",
    "create_verifier_participant",
    "create_generator_participant",
    "create_planner_agent",
    "create_executor_agent",
    "create_verifier_agent",
    "create_generator_agent",
    "DynamicWorkflowParticipants",
    "create_default_dynamic_participants",
]
