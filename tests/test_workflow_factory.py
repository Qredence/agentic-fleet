"""
Tests for WorkflowFactory.
"""

from pathlib import Path

import pytest

from agentic_fleet.utils.factory import WorkflowFactory
from agentic_fleet.workflow.magentic_workflow import MagenticFleetWorkflow


def _validate_workflow_dict(workflow: dict) -> None:
    assert "id" in workflow
    assert "name" in workflow
    assert "description" in workflow
    assert "factory" in workflow
    assert "agent_count" in workflow


def test_workflow_factory_initialization() -> None:
    """Test WorkflowFactory initializes correctly."""
    factory = WorkflowFactory()

    assert factory.config_path is not None
    assert factory._config is not None


def test_workflow_factory_list_workflows() -> None:
    """Test listing available workflows."""
    factory = WorkflowFactory()
    workflows = factory.list_available_workflows()

    assert isinstance(workflows, list)
    workflow_ids = {workflow["id"] for workflow in workflows}
    assert workflow_ids == {"collaboration", "magentic_fleet"}

    for workflow in workflows:
        _validate_workflow_dict(workflow)


def test_get_workflow_config_magentic_fleet() -> None:
    """Test getting magentic fleet workflow config."""
    factory = WorkflowFactory()
    config = factory.get_workflow_config("magentic_fleet")
    assert config.name == "Magentic Fleet Workflow"


def test_get_workflow_config_collaboration() -> None:
    """Test getting collaboration workflow config."""
    factory = WorkflowFactory()
    config = factory.get_workflow_config("collaboration")
    assert config.name == "Collaboration Workflow"


def test_create_workflow_collaboration() -> None:
    """Test creating collaboration workflow instance."""
    factory = WorkflowFactory()
    workflow = factory.create_workflow("collaboration")
    # Check it returns a workflow instance
    assert workflow is not None


def test_create_workflow_magentic_fleet() -> None:
    """Test creating magentic fleet workflow instance."""
    factory = WorkflowFactory()
    workflow = factory.create_workflow("magentic_fleet")
    assert isinstance(workflow, MagenticFleetWorkflow)


@pytest.mark.skip(reason="Legacy test for removed api.workflow_factory implementation")
def test_build_magentic_fleet_args() -> None:
    """Test building arguments for magentic fleet workflow."""
    pass


@pytest.mark.skip(reason="utils.factory.WorkflowFactory doesn't check config/ directory anymore")
def test_workflow_factory_with_custom_path() -> None:
    """Test WorkflowFactory with custom config path to repo override."""
    pass


def test_workflow_factory_missing_config_file() -> None:
    """Test WorkflowFactory raises FileNotFoundError for missing config."""
    with pytest.raises(FileNotFoundError):
        WorkflowFactory(config_path=Path("/nonexistent/config.yaml"))


def test_get_workflow_config_invalid_workflow() -> None:
    """Test getting config for invalid workflow name."""
    factory = WorkflowFactory()
    with pytest.raises(ValueError, match="Unknown workflow"):
        factory.get_workflow_config("invalid_workflow")


def test_create_workflow_invalid_name() -> None:
    """Test creating workflow with invalid name."""
    factory = WorkflowFactory()
    with pytest.raises(ValueError, match="Unknown workflow"):
        factory.create_workflow("invalid_workflow")


def test_workflow_factory_config_structure() -> None:
    """Test that workflow config has expected structure."""
    factory = WorkflowFactory()

    workflows = factory.list_available_workflows()
    assert len(workflows) > 0

    # Each workflow should have required fields
    for workflow in workflows:
        assert "id" in workflow
        assert "name" in workflow
        assert "description" in workflow
        assert "factory" in workflow
        assert "agent_count" in workflow


def test_workflow_factory_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test WorkflowFactory respects AF_WORKFLOW_CONFIG environment variable."""
    # Create a temporary config file path
    config_path = Path(__file__).parent / "fixtures" / "test_workflows.yaml"

    # If the fixture exists, test the override
    if config_path.exists():
        monkeypatch.setenv("AF_WORKFLOW_CONFIG", str(config_path))
        factory = WorkflowFactory()
        assert factory.config_path == config_path


@pytest.mark.skip(reason="utils.factory.WorkflowFactory uses package default, not config/ fallback")
def test_workflow_factory_env_invalid_path_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid AF_WORKFLOW_CONFIG should fall back to repo configuration."""
    pass
