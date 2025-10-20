from __future__ import annotations

import pytest

agent_framework = pytest.importorskip("agent_framework")


from agenticfleet.workflows._experimental_dynamic import (  # noqa: E402
    create_default_dynamic_participants,
    create_dynamic_workflow,
)


def test_default_backbone_participants_present() -> None:
    participants = create_default_dynamic_participants(include_tool_agents=False)
    assert set(participants.backbone.keys()) == {"planner", "executor", "verifier", "generator"}
    assert participants.tools == {}


def test_dynamic_workflow_builds_with_backbone_only() -> None:
    participants = create_default_dynamic_participants(include_tool_agents=False)
    workflow = create_dynamic_workflow(
        participants=participants.as_dict(),
        include_default_tool_agents=False,
    )
    assert hasattr(workflow, "run")
