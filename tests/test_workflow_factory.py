"""Tests for WorkflowFactory."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agentic_fleet.utils.factory import WorkflowFactory


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
    workflow_ids = {w["id"] for w in workflows}
    assert workflow_ids == {"magentic_fleet"}

    for workflow in workflows:
        assert "id" in workflow
        assert "name" in workflow
        assert "description" in workflow
        assert "factory" in workflow
        assert "agent_count" in workflow


def test_get_workflow_config_magentic_fleet() -> None:
    """Test getting magentic fleet workflow config."""
    factory = WorkflowFactory()
    config = factory.get_workflow_config("magentic_fleet")
    assert config.name == "Magentic Fleet Workflow"
    assert config.factory == "create_magentic_fleet_workflow"
    assert set(config.agents) >= {"planner", "executor", "coder", "verifier", "generator"}


def test_get_workflow_config_not_found() -> None:
    """Test getting non-existent workflow config raises ValueError."""
    factory = WorkflowFactory()

    with pytest.raises(ValueError, match="Workflow 'nonexistent' not found"):
        factory.get_workflow_config("nonexistent")


def test_create_from_yaml_magentic_fleet() -> None:
    """Test creating magentic fleet workflow from YAML."""
    import os

    factory = WorkflowFactory()
    # Skip if OPENAI_API_KEY not set (will fail without it)
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set - skipping workflow creation test")

    # Should not raise NotImplementedError anymore - should create workflow
    workflow = factory.create_from_yaml("magentic_fleet")
    assert workflow is not None


def test_build_magentic_fleet_args() -> None:
    """Test building arguments for magentic fleet workflow."""
    factory = WorkflowFactory()
    config = factory.get_workflow_config("magentic_fleet")

    # Test that we can build a workflow using the builder
    # Skip if OPENAI_API_KEY not set (will use stub workflow)
    import os

    from agentic_fleet.workflow.magentic_workflow import MagenticFleetWorkflowBuilder

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    builder = MagenticFleetWorkflowBuilder()
    workflow = builder.build(config)

    assert workflow is not None


def test_workflow_factory_with_custom_path(tmp_path: Path) -> None:
    """Test WorkflowFactory with an explicit custom path (temp file)."""
    custom = tmp_path / "custom_workflows.yaml"
    custom.write_text(
        yaml.safe_dump(
            {
                "workflows": {
                    "mini": {
                        "name": "Mini Workflow",
                        "description": "Custom minimal workflow",
                        "factory": "create_magentic_fleet_workflow",
                        "agents": {"solo": "agents.planner"},
                        "manager": {"model": "gpt-5-mini"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    factory = WorkflowFactory(config_path=custom)
    assert factory.config_path == custom
    cfg = factory.get_workflow_config("mini")
    assert cfg.name == "Mini Workflow"


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


def test_workflow_factory_env_invalid_path_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid AF_WORKFLOW_CONFIG should fall back to packaged default."""
    monkeypatch.setenv("AF_WORKFLOW_CONFIG", str(Path("/definitely/missing.yaml")))
    factory = WorkflowFactory()
    assert factory.config_path.name == "workflows.yaml"
    workflows = {w["id"] for w in factory.list_available_workflows()}
    assert "magentic_fleet" in workflows


def test_resolve_agent_config_from_module() -> None:
    """Test resolving agent config from Python module reference."""
    factory = WorkflowFactory()

    # Test resolving agent config from module
    resolved = factory._resolve_agent_config("agents.planner")

    assert isinstance(resolved, dict)
    assert resolved["model"] == "gpt-5-mini"
    assert resolved["instructions"] == "prompts.planner"
    assert (
        resolved["description"]
        == "Decomposes the request into actionable steps and assigns ownership"
    )
    assert resolved["temperature"] == 0.5


def test_resolve_agent_config_inline_dict() -> None:
    """Test backward compatibility with inline agent config dict."""
    factory = WorkflowFactory()

    inline_config = {
        "model": "gpt-5-mini",
        "instructions": "Custom instructions",
        "temperature": 0.7,
    }

    resolved = factory._resolve_agent_config(inline_config)

    assert resolved == inline_config


def test_resolve_agent_config_invalid_module() -> None:
    """Test resolving agent config from non-existent module falls back gracefully."""
    factory = WorkflowFactory()

    # Should fall back to treating as instructions string
    resolved = factory._resolve_agent_config("agents.nonexistent")

    assert isinstance(resolved, dict)
    assert resolved["instructions"] == "agents.nonexistent"


def test_resolve_instructions_from_prompt_module() -> None:
    """Test resolving instructions from Python prompt module."""
    from agentic_fleet.agents.coordinator import AgentFactory

    factory = AgentFactory()

    # Test resolving prompt from module
    resolved = factory._resolve_instructions("prompts.planner")

    assert isinstance(resolved, str)
    assert "planner" in resolved.lower() or "break down" in resolved.lower()
    assert len(resolved) > 0


def test_resolve_instructions_inline_string() -> None:
    """Test backward compatibility with inline instructions string."""
    from agentic_fleet.agents.coordinator import AgentFactory

    factory = AgentFactory()

    inline_instructions = "You are a helpful assistant."

    resolved = factory._resolve_instructions(inline_instructions)

    assert resolved == inline_instructions


def test_resolve_instructions_invalid_module() -> None:
    """Test resolving instructions from non-existent module falls back gracefully."""
    from agentic_fleet.agents.coordinator import AgentFactory

    factory = AgentFactory()

    # Should fall back to using as-is
    resolved = factory._resolve_instructions("prompts.nonexistent")

    assert resolved == "prompts.nonexistent"


def test_workflow_config_with_module_references() -> None:
    """Test workflow config resolution with Python module references."""
    factory = WorkflowFactory()
    config = factory.get_workflow_config("magentic_fleet")

    # All agents should be resolved to dicts (not strings)
    assert isinstance(config.agents, dict)
    for agent_name, agent_config in config.agents.items():
        assert isinstance(
            agent_config, dict
        ), f"Agent {agent_name} config should be resolved to dict"
        assert "model" in agent_config, f"Agent {agent_name} missing model"
        assert "instructions" in agent_config, f"Agent {agent_name} missing instructions"


def test_workflow_config_backward_compatible_inline() -> None:
    """Test workflow config works with inline agent configs (backward compatibility)."""
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(
            {
                "workflows": {
                    "test_inline": {
                        "name": "Test Inline Workflow",
                        "description": "Test backward compatibility",
                        "factory": "create_test_workflow",
                        "agents": {
                            "test_agent": {
                                "model": "gpt-5-mini",
                                "instructions": "Test instructions",
                                "temperature": 0.5,
                            }
                        },
                        "manager": {"model": "gpt-5-mini"},
                    }
                }
            },
            f,
        )
        temp_path = Path(f.name)

    try:
        factory = WorkflowFactory(config_path=temp_path)
        config = factory.get_workflow_config("test_inline")

        # Should work with inline configs
        assert config.agents["test_agent"]["model"] == "gpt-5-mini"
        assert config.agents["test_agent"]["instructions"] == "Test instructions"
    finally:
        temp_path.unlink()
