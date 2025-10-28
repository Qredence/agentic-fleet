from __future__ import annotations

from agenticfleet import create_collaboration_workflow


def test_collaboration_workflow_builds_expected_participants() -> None:
    workflow = create_collaboration_workflow()

    executor_ids = {executor.id for executor in workflow.get_executors_list()}

    assert executor_ids == {
        "magentic_orchestrator",
        "agent_researcher",
        "agent_coder",
        "agent_reviewer",
    }
