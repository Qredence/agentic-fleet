"""Tests for WorkflowFactory."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agentic_fleet.models.workflow_config import WorkflowConfig
from agentic_fleet.utils.factory import WorkflowFactory
from agentic_fleet.workflow.magentic_workflow import MagenticFleetWorkflow


def _validate_workflow_dict(workflow: dict) -> None:
    assert "id" in workflow
    assert "name" in workflow
    assert "description" in workflow
    assert "factory" in workflow
    assert "agent_count" in workflow


def _write_workflows_yaml(path: Path, workflows: dict[str, dict]) -> None:
    """Write workflows mapping to a YAML file."""
    path.write_text(yaml.safe_dump({"workflows": workflows}), encoding="utf-8")


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
    workflow_ids = {workflow["id"] for workflow in workflows}
    assert workflow_ids == {"collaboration", "magentic_fleet"}

    for workflow in workflows:
        _validate_workflow_dict(workflow)


def test_get_workflow_config_magentic_fleet() -> None:
    """Test getting magentic fleet workflow config."""
    factory = WorkflowFactory()
    config = factory.get_workflow_config("magentic_fleet")
    assert isinstance(config, WorkflowConfig)
    assert config.name == "Magentic Fleet Workflow"
    assert config.factory == "create_magentic_fleet_workflow"
    assert set(config.agents) >= {"planner", "executor", "coder", "verifier", "generator"}


def test_get_workflow_config_serialization_round_trip() -> None:
    """WorkflowConfig should serialize back to a dictionary."""
    factory = WorkflowFactory()
    config = factory.get_workflow_config("magentic_fleet")

    # Support environments running Pydantic v1 (no model_dump) by falling back to dict()
    # Fallback order: model_dump (pydantic v2) -> export_model (custom) -> raw __dict__ snapshot
    if hasattr(config, "model_dump"):
        serialized = config.model_dump()  # type: ignore[assignment]
    else:
        serialized = {
            k: getattr(config, k)
            for k in dir(config)
            if not k.startswith("_") and not callable(getattr(config, k))
        }

    assert serialized["id"] == "magentic_fleet"
    assert serialized["factory"] == config.factory
    assert isinstance(serialized["agents"], dict)
    assert isinstance(serialized["manager"], dict)


def test_get_workflow_config_not_found() -> None:
    """Test getting non-existent workflow config raises ValueError."""
    factory = WorkflowFactory()

    with pytest.raises(ValueError, match="Workflow 'nonexistent' not found"):
        factory.get_workflow_config("nonexistent")


def test_create_from_yaml_magentic_fleet(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test creating magentic fleet workflow from YAML."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    factory = WorkflowFactory()
    workflow = factory.create_from_yaml("magentic_fleet")

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
        WorkflowFactory(config_path=Path("/nonexistent/path.yaml"))


def test_workflow_factory_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """WorkflowFactory should honour AF_WORKFLOW_CONFIG when file exists."""

    override = tmp_path / "custom_workflows.yaml"
    override.write_text(
        yaml.safe_dump(
            {
                "workflows": {
                    "custom": {
                        "name": "Custom Workflow",
                        "description": "Loaded via env override",
                        "factory": "create_custom_workflow",
                        "agents": {"solo": {"model": "gpt-5-nano"}},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("AF_WORKFLOW_CONFIG", str(override))

    factory = WorkflowFactory()

    assert factory.config_path == override
    workflows = factory.list_available_workflows()
    assert [workflow["id"] for workflow in workflows] == ["custom"]

    config = factory.get_workflow_config("custom")
    assert config.name == "Custom Workflow"
    assert config.factory == "create_custom_workflow"
    assert config.agents == {"solo": {"model": "gpt-5-nano"}}


@pytest.mark.skip(reason="utils.factory.WorkflowFactory uses package default, not config/ fallback")
def test_workflow_factory_env_invalid_path_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid AF_WORKFLOW_CONFIG should fall back to repo configuration."""
    pass
