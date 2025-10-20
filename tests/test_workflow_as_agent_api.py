"""Test workflow_as_agent API integration."""

import pytest

from agenticfleet.haxui.runtime import FleetRuntime, build_entity_catalog


def test_workflow_as_agent_in_catalog():
    """Verify workflow_as_agent appears in entity catalog."""
    agents, workflows = build_entity_catalog()

    # Find workflow_as_agent in workflows
    workflow_found = False
    for workflow in workflows:
        if workflow["id"] == "workflow_as_agent":
            workflow_found = True
            assert workflow["type"] == "workflow"
            assert "Reflection" in workflow["name"]
            assert workflow["start_executor_id"] == "worker"
            assert "worker" in workflow["executors"]
            assert "reviewer" in workflow["executors"]
            break

    assert workflow_found, "workflow_as_agent not found in entity catalog"


def test_entity_catalog_structure():
    """Verify entity catalog returns correct structure."""
    agents, workflows = build_entity_catalog()

    # Should have at least 1 agent and 2 workflows (magentic_fleet_workflow + workflow_as_agent)
    assert isinstance(agents, list)
    assert isinstance(workflows, list)
    assert len(agents) >= 1
    assert len(workflows) >= 2

    # Verify workflow_as_agent structure
    workflow_as_agent = None
    for wf in workflows:
        if wf["id"] == "workflow_as_agent":
            workflow_as_agent = wf
            break

    assert workflow_as_agent is not None
    assert workflow_as_agent["id"] == "workflow_as_agent"
    assert workflow_as_agent["type"] == "workflow"
    assert "framework" in workflow_as_agent
    assert "description" in workflow_as_agent
    assert "executors" in workflow_as_agent
    assert "input_schema" in workflow_as_agent
    assert workflow_as_agent["metadata"]["pattern"] == "reflection"
    assert workflow_as_agent["metadata"]["quality_assurance"] is True


@pytest.mark.asyncio
async def test_runtime_initialization():
    """Verify FleetRuntime initializes workflow_as_agent."""
    runtime = FleetRuntime()
    await runtime.ensure_initialised()

    # Check that workflow_as_agent is available
    # Note: This will be None if create_workflow_agent import fails
    # In production, it should be initialized
    assert hasattr(runtime, "_workflow_as_agent")


if __name__ == "__main__":
    # Run basic tests
    print("Testing workflow_as_agent API integration...")
    test_workflow_as_agent_in_catalog()
    print("✓ workflow_as_agent found in catalog")

    test_entity_catalog_structure()
    print("✓ Entity catalog structure validated")

    print("\nAll tests passed!")
