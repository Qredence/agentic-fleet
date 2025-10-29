"""Tests for WorkflowFactory."""

from __future__ import annotations

from pathlib import Path

import pytest

from agenticfleet.api.workflow_factory import WorkflowFactory


def test_workflow_factory_initialization() -> None:
    """Test WorkflowFactory initializes correctly."""
    factory = WorkflowFactory()
    assert factory.config_path.exists()
    assert factory._config is not None


def test_list_available_workflows() -> None:
    """Test listing available workflows."""
    factory = WorkflowFactory()
    workflows = factory.list_available_workflows()

    assert isinstance(workflows, list)
    assert len(workflows) == 2  # collaboration and magentic_fleet

    # Check metadata structure
    for workflow in workflows:
        assert "id" in workflow
        assert "name" in workflow
        assert "description" in workflow
        assert "factory" in workflow
        assert "agent_count" in workflow


def test_get_workflow_config_collaboration() -> None:
    """Test getting collaboration workflow config."""
    factory = WorkflowFactory()
    config = factory.get_workflow_config("collaboration")

    assert config.name == "Collaboration Workflow"
    assert config.factory == "create_collaboration_workflow"
    assert len(config.agents) == 3  # researcher, coder, reviewer
    assert "researcher" in config.agents
    assert "coder" in config.agents
    assert "reviewer" in config.agents


def test_get_workflow_config_magentic_fleet() -> None:
    """Test getting magentic fleet workflow config."""
    factory = WorkflowFactory()
    config = factory.get_workflow_config("magentic_fleet")

    assert config.name == "Magentic Fleet Workflow"
    assert config.factory == "create_magentic_fleet_workflow"
    assert len(config.agents) == 5  # planner, executor, coder, verifier, generator
    assert "planner" in config.agents
    assert "executor" in config.agents
    assert "coder" in config.agents
    assert "verifier" in config.agents
    assert "generator" in config.agents


def test_get_workflow_config_not_found() -> None:
    """Test getting non-existent workflow config raises ValueError."""
    factory = WorkflowFactory()

    with pytest.raises(ValueError, match="Workflow 'nonexistent' not found"):
        factory.get_workflow_config("nonexistent")


def test_create_from_yaml_collaboration() -> None:
    """Test creating collaboration workflow from YAML."""
    factory = WorkflowFactory()
    workflow = factory.create_from_yaml("collaboration")

    assert workflow is not None
    # Workflow should be a Magentic workflow instance
    assert hasattr(workflow, "run")


def test_create_from_yaml_magentic_fleet() -> None:
    """Test creating magentic fleet workflow from YAML."""
    factory = WorkflowFactory()
    workflow = factory.create_from_yaml("magentic_fleet")

    assert workflow is not None
    assert hasattr(workflow, "run")


def test_build_collaboration_args() -> None:
    """Test building arguments for collaboration workflow."""
    factory = WorkflowFactory()
    config = factory.get_workflow_config("collaboration")

    kwargs = factory._build_collaboration_args(config)

    assert "researcher_instructions" in kwargs
    assert "coder_instructions" in kwargs
    assert "reviewer_instructions" in kwargs
    assert "manager_instructions" in kwargs
    assert "max_round_count" in kwargs
    assert "max_stall_count" in kwargs
    assert "max_reset_count" in kwargs
    assert "participant_model" in kwargs
    assert "manager_model" in kwargs


def test_build_magentic_fleet_args() -> None:
    """Test building arguments for magentic fleet workflow."""
    factory = WorkflowFactory()
    config = factory.get_workflow_config("magentic_fleet")

    kwargs = factory._build_magentic_fleet_args(config)

    assert "planner_instructions" in kwargs
    assert "executor_instructions" in kwargs
    assert "coder_instructions" in kwargs
    assert "verifier_instructions" in kwargs
    assert "generator_instructions" in kwargs
    assert "manager_instructions" in kwargs
    assert "planner_model" in kwargs
    assert "executor_model" in kwargs
    assert "coder_model" in kwargs
    assert "verifier_model" in kwargs
    assert "generator_model" in kwargs
    assert "manager_model" in kwargs


def test_workflow_factory_with_custom_path() -> None:
    """Test WorkflowFactory with custom config path."""
    config_path = Path(__file__).parent.parent / "src" / "agenticfleet" / "magentic_fleet.yaml"
    factory = WorkflowFactory(config_path=config_path)

    assert factory.config_path == config_path
    assert factory._config is not None


def test_workflow_factory_missing_config_file() -> None:
    """Test WorkflowFactory raises FileNotFoundError for missing config."""
    with pytest.raises(FileNotFoundError):
        WorkflowFactory(config_path="/nonexistent/path.yaml")
