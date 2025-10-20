"""Participant bundle for the dynamic workflow."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from agent_framework import AgentProtocol

from ..tools import create_tool_participants
from .backbone import create_backbone_participants


@dataclass(frozen=True)
class DynamicWorkflowParticipants:
    """Container for backbone + tool participants."""

    backbone: Mapping[str, AgentProtocol]
    tools: Mapping[str, AgentProtocol]

    def as_dict(self) -> dict[str, AgentProtocol]:
        """Blend backbone and tool participants into a single mapping."""
        combined: dict[str, AgentProtocol] = {}
        combined.update(self.backbone)
        combined.update(self.tools)
        return combined


def create_default_dynamic_participants(
    *,
    include_tool_agents: bool = True,
) -> DynamicWorkflowParticipants:
    """Create the default participant bundle."""
    backbone = create_backbone_participants()
    tools = create_tool_participants(include_tool_agents=include_tool_agents)
    return DynamicWorkflowParticipants(backbone=backbone, tools=tools)


__all__ = ["DynamicWorkflowParticipants", "create_default_dynamic_participants"]
