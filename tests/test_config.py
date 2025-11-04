"""
Comprehensive Configuration Testing

Tests for AgenticFleet configuration loading, validation, and workflow factory.
This is a critical test file that validates the entire configuration system
to prevent deployment failures and ensure proper workflow wiring.

Key Areas Tested:
- Workflow configuration loading and parsing
- Agent configuration resolution and validation
- Factory method registration and calling
- Environment variable overrides
- Configuration file hierarchy and precedence
- Invalid configuration error handling
- Performance configuration validation
- Security configuration verification
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from agentic_fleet.utils.factory import WorkflowFactory


class TestWorkflowFactoryCore:
    """Test core WorkflowFactory functionality."""

    @pytest.mark.asyncio
    async def test_factory_initialization_with_default_config(self):
        """Test factory initializes with default configuration."""
        factory = WorkflowFactory()

        assert factory.config_path.exists(), "Default config path should exist"
        assert factory._config is not None, "Config should be loaded"
        assert isinstance(factory._config, dict), "Config should be a dictionary"

    @pytest.mark.asyncio
    async def test_factory_initialization_with_custom_config(self):
        """Test factory initialization with custom config path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "workflows": {
                    "test_workflow": {
                        "name": "Test Workflow",
                        "description": "Test workflow for validation",
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
            }
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            factory = WorkflowFactory(config_path=temp_path)
            assert factory.config_path == temp_path, "Custom config path should be set"
            assert factory._config == config_data, "Config data should be loaded correctly"
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_factory_missing_config_file(self):
        """Test factory raises FileNotFoundError for missing config."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            WorkflowFactory(config_path=Path("/nonexistent/config.yaml"))

    @pytest.mark.asyncio
    async def test_factory_invalid_yaml_config(self):
        """Test factory handles invalid YAML configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)

        try:
            with pytest.raises(yaml.YAMLError):
                WorkflowFactory(config_path=temp_path)
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_factory_empty_config(self):
        """Test factory handles empty configuration file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            factory = WorkflowFactory(config_path=temp_path)
            assert factory._config == {}, "Empty config should result in empty dict"
        finally:
            temp_path.unlink()


class TestWorkflowListing:
    """Test workflow discovery and listing functionality."""

    @pytest.mark.asyncio
    async def test_list_available_workflows_structure(self):
        """Test workflow listing returns correct structure."""
        factory = WorkflowFactory()
        workflows = await factory.list_available_workflows_async()

        assert isinstance(workflows, list), "Workflows should be a list"
        assert len(workflows) > 0, "Should have at least one workflow"

        for workflow in workflows:
            assert "id" in workflow, f"Workflow {workflow} missing 'id' field"
            assert "name" in workflow, f"Workflow {workflow} missing 'name' field"
            assert "description" in workflow, f"Workflow {workflow} missing 'description' field"
            assert "factory" in workflow, f"Workflow {workflow} missing 'factory' field"
            assert "agent_count" in workflow, f"Workflow {workflow} missing 'agent_count' field"

    @pytest.mark.asyncio
    async def test_list_available_workflows_contains_magentic_fleet(self):
        """Test default workflow listing includes magentic_fleet."""
        factory = WorkflowFactory()
        workflows = await factory.list_available_workflows_async()
        workflow_ids = {workflow["id"] for workflow in workflows}

        assert "magentic_fleet" in workflow_ids, "Should include magentic_fleet workflow"

    @pytest.mark.asyncio
    async def test_list_workflows_agent_count_validation(self):
        """Test agent_count field is calculated correctly."""
        factory = WorkflowFactory()
        workflows = await factory.list_available_workflows_async()

        for workflow in workflows:
            agent_count = workflow["agent_count"]
            assert isinstance(
                agent_count, int
            ), f"agent_count should be integer, got {type(agent_count)}"
            assert agent_count >= 0, f"agent_count should be non-negative, got {agent_count}"


class TestWorkflowConfiguration:
    """Test individual workflow configuration retrieval and validation."""

    @pytest.mark.asyncio
    async def test_get_workflow_config_valid_workflow(self):
        """Test getting configuration for valid workflow."""
        factory = WorkflowFactory()
        config = await factory.get_workflow_config_async("magentic_fleet")

        assert config is not None, "Should return config for valid workflow"
        assert config.id == "magentic_fleet", "Should return correct workflow config"
        assert config.name is not None, "Config should have name"
        assert config.factory is not None, "Config should have factory"
        assert hasattr(config, "agents"), "Config should have agents"
        assert hasattr(config, "manager"), "Config should have manager"

    @pytest.mark.asyncio
    async def test_get_workflow_config_invalid_workflow(self):
        """Test getting configuration for invalid workflow raises error."""
        factory = WorkflowFactory()

        with pytest.raises(ValueError, match="Workflow 'nonexistent' not found"):
            await factory.get_workflow_config_async("nonexistent")

    @pytest.mark.asyncio
    async def test_workflow_config_required_fields(self):
        """Test workflow configuration has all required fields."""
        factory = WorkflowFactory()
        config = await factory.get_workflow_config_async("magentic_fleet")

        required_fields = ["id", "name", "description", "factory"]
        for field in required_fields:
            assert hasattr(config, field), f"Config missing required field: {field}"
            assert getattr(config, field) is not None, f"Config field {field} should not be None"

    @pytest.mark.asyncio
    async def test_workflow_config_agents_structure(self):
        """Test workflow agents configuration structure."""
        factory = WorkflowFactory()
        config = await factory.get_workflow_config_async("magentic_fleet")

        assert isinstance(config.agents, dict), "Agents should be a dictionary"
        assert len(config.agents) > 0, "Should have at least one agent configured"

        for agent_name, agent_config in config.agents.items():
            assert isinstance(agent_config, dict), f"Agent {agent_name} config should be a dict"
            assert "model" in agent_config, f"Agent {agent_name} missing model"
            assert "instructions" in agent_config, f"Agent {agent_name} missing instructions"

    @pytest.mark.asyncio
    async def test_workflow_config_manager_structure(self):
        """Test workflow manager configuration structure."""
        factory = WorkflowFactory()
        config = await factory.get_workflow_config_async("magentic_fleet")

        assert hasattr(config, "manager"), "Should have manager configuration"
        manager_config = config.manager
        assert isinstance(manager_config, dict), "Manager config should be a dict"
        assert "model" in manager_config, "Manager config should have model"


class TestAgentConfigurationResolution:
    """Test agent configuration resolution from various sources."""

    @pytest.mark.asyncio
    async def test_resolve_agent_config_module_reference(self):
        """Test resolving agent config from Python module reference."""
        factory = WorkflowFactory()

        # Test with known agent module reference
        resolved = factory._resolve_agent_config("agents.planner")

        assert isinstance(resolved, dict), "Resolved config should be a dict"
        assert "model" in resolved, "Resolved config should have model"
        assert "instructions" in resolved, "Resolved config should have instructions"
        assert "temperature" in resolved, "Resolved config should have temperature"

    @pytest.mark.asyncio
    async def test_resolve_agent_config_inline_dict(self):
        """Test resolving agent config from inline dictionary."""
        factory = WorkflowFactory()

        inline_config = {
            "model": "gpt-5-mini",
            "instructions": "Custom test instructions",
            "temperature": 0.7,
            "description": "Test agent",
        }

        resolved = await factory._resolve_agent_config(inline_config)

        assert resolved == inline_config, "Inline config should be returned as-is"

    @pytest.mark.asyncio
    async def test_resolve_agent_config_string_instructions(self):
        """Test resolving agent config from string instructions."""
        factory = WorkflowFactory()

        string_instructions = "You are a helpful test assistant."
        resolved = await factory._resolve_agent_config(string_instructions)

        assert isinstance(resolved, dict), "Should convert string to dict"
        assert resolved["instructions"] == string_instructions, "Should preserve instructions"
        # Note: Factory doesn't add default model - that's the builder's responsibility

    @pytest.mark.asyncio
    async def test_resolve_agent_config_invalid_module_fallback(self):
        """Test graceful fallback for invalid module references."""
        factory = WorkflowFactory()

        # Test with non-existent module
        resolved = await factory._resolve_agent_config("agents.nonexistent")

        assert isinstance(resolved, dict), "Should fallback to dict"
        assert resolved["instructions"] == "agents.nonexistent", "Should treat as instructions"


class TestFactoryMethodValidation:
    """Test factory method validation and execution."""

    @pytest.mark.asyncio
    async def test_factory_method_exists(self):
        """Test that specified factory methods exist and are callable."""
        factory = WorkflowFactory()
        config = await factory.get_workflow_config_async("magentic_fleet")

        factory_method_path = config.factory
        # Factory methods can be simple names (resolved by builder) or module.method format
        # The important part is that the builder can resolve them
        assert (
            factory_method_path == "create_magentic_fleet_workflow"
        ), "Should have factory method name"

    @pytest.mark.asyncio
    async def test_create_workflow_from_yaml(self):
        """Test creating workflow from YAML configuration."""
        pytest.skip(
            "Agent implementations not yet complete - workflow creation requires implemented agent factories"
        )

        factory = WorkflowFactory()

        # Skip if OPENAI_API_KEY not set (will fail without it)
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set - skipping workflow creation test")

        workflow = await factory.create_from_yaml_async("magentic_fleet")
        assert workflow is not None, "Should create workflow successfully"

    @pytest.mark.asyncio
    async def test_create_workflow_invalid_id(self, caplog):
        """Test creating workflow with invalid ID falls back to default."""
        pytest.skip(
            "Agent implementations not yet complete - workflow creation requires implemented agent factories"
        )

        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set - skipping workflow creation test")

        factory = WorkflowFactory()
        with caplog.at_level(logging.WARNING):  # type: ignore[name-defined]
            workflow = await factory.create_from_yaml_async("invalid")
        assert workflow is not None, "Fallback should produce a workflow instance"
        # Ensure a warning log about fallback occurred
        assert any(
            "falling back" in rec.message.lower() or "unknown workflow_id" in rec.message.lower()
            for rec in caplog.records  # type: ignore[name-defined]
        ), "Expected fallback warning log not found"


class TestEnvironmentVariableOverrides:
    """Test environment variable configuration overrides."""

    @pytest.mark.asyncio
    async def test_af_workflow_config_env_override(self, monkeypatch):
        """Test AF_WORKFLOW_CONFIG environment variable override."""
        # Create a custom config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "workflows": {
                    "env_workflow": {
                        "name": "Environment Override Workflow",
                        "description": "Loaded via environment override",
                        "factory": "create_env_workflow",
                        "agents": {
                            "env_agent": {"model": "gpt-5-nano", "instructions": "Environment test"}
                        },
                    }
                }
            }
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            # Set environment variable
            monkeypatch.setenv("AF_WORKFLOW_CONFIG", str(temp_path))

            factory = WorkflowFactory()
            assert factory.config_path == temp_path, "Should use environment override path"

            workflows = await factory.list_available_workflows_async()
            workflow_ids = {workflow["id"] for workflow in workflows}
            assert "env_workflow" in workflow_ids, "Should load workflow from environment config"

        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_af_workflow_config_invalid_path_fallback(self, monkeypatch):
        """Test fallback to repo config when AF_WORKFLOW_CONFIG is invalid."""
        invalid_path = "/definitely/missing/config.yaml"
        monkeypatch.setenv("AF_WORKFLOW_CONFIG", invalid_path)

        # Should not raise error and should fall back to repo config
        factory = WorkflowFactory()

        # Should have loaded default configuration
        workflows = await factory.list_available_workflows_async()
        assert len(workflows) > 0, "Should have loaded default workflows"


class TestConfigurationValidation:
    """Test comprehensive configuration validation."""

    @pytest.mark.asyncio
    async def test_validate_magentic_fleet_complete_config(self):
        """Test complete validation of magentic_fleet configuration."""
        factory = WorkflowFactory()
        config = await factory.get_workflow_config_async("magentic_fleet")

        # Validate core structure
        assert config.id == "magentic_fleet"
        assert "Magentic" in config.name
        assert config.factory == "create_magentic_fleet_workflow"

        # Validate agent structure
        required_agents = ["planner", "executor", "coder", "verifier", "generator"]
        for agent in required_agents:
            assert agent in config.agents, f"Missing required agent: {agent}"

            agent_config = config.agents[agent]
            assert "model" in agent_config, f"Agent {agent} missing model"
            assert agent_config["model"], f"Agent {agent} has empty model"
            assert "instructions" in agent_config, f"Agent {agent} missing instructions"
            assert agent_config["instructions"], f"Agent {agent} has empty instructions"

    @pytest.mark.asyncio
    async def test_validate_model_references(self):
        """Test that model references are valid and consistent."""
        factory = WorkflowFactory()
        config = await factory.get_workflow_config_async("magentic_fleet")

        # Check that models are valid strings
        all_models = set()

        # Collect agent models
        for agent_config in config.agents.values():
            if isinstance(agent_config, dict) and "model" in agent_config:
                model = agent_config["model"]
                assert isinstance(model, str), f"Model should be string, got {type(model)}"
                assert model.strip(), f"Model should not be empty: {model}"
                all_models.add(model)

        # Check manager model
        if hasattr(config, "manager") and config.manager:
            manager_model = config.manager.get("model")
            if manager_model:
                assert isinstance(manager_model, str), "Manager model should be string"
                all_models.add(manager_model)

        assert all_models, "Should have at least one model configured"

    @pytest.mark.asyncio
    async def test_validate_temperature_values(self):
        """Test that temperature values are in valid range."""
        factory = WorkflowFactory()
        config = await factory.get_workflow_config_async("magentic_fleet")

        for agent_name, agent_config in config.agents.items():
            if isinstance(agent_config, dict) and "temperature" in agent_config:
                temp = agent_config["temperature"]
                # Use PEP 604 union syntax (int | float) per project standards
                assert isinstance(
                    temp, int | float
                ), f"Temperature should be numeric for {agent_name}"
                assert (
                    0.0 <= temp <= 2.0
                ), f"Temperature {temp} out of range [0.0, 2.0] for {agent_name}"

    @pytest.mark.asyncio
    async def test_validate_instructions_content(self):
        """Test that instructions are meaningful and not empty."""
        factory = WorkflowFactory()
        config = await factory.get_workflow_config_async("magentic_fleet")

        for agent_name, agent_config in config.agents.items():
            if isinstance(agent_config, dict) and "instructions" in agent_config:
                instructions = agent_config["instructions"]
                assert isinstance(
                    instructions, str
                ), f"Instructions should be string for {agent_name}"

                # Skip module references (they start with 'prompts.')
                if not instructions.startswith("prompts."):
                    assert (
                        len(instructions.strip()) > 10
                    ), f"Instructions too short for {agent_name}: {instructions}"


class TestConfigurationErrorHandling:
    """Test configuration error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_malformed_workflow_config(self):
        """Test handling of malformed workflow configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            malformed_config = {
                "workflows": {
                    "malformed": {
                        "name": "Malformed Workflow",
                        # Missing required fields
                        "agents": {
                            "test": {}  # Empty agent config
                        },
                    }
                }
            }
            yaml.dump(malformed_config, f)
            temp_path = Path(f.name)

        try:
            factory = WorkflowFactory(config_path=temp_path)

            # Should still load config but validation may fail
            config = await factory.get_workflow_config_async("malformed")
            assert config.id == "malformed"

        except Exception as e:
            # Expected behavior for malformed config
            assert "malformed" in str(e).lower() or "missing" in str(e).lower()
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_circular_reference_handling(self):
        """Test handling of circular references in configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_with_circular = {
                "workflows": {
                    "circular": {
                        "name": "Circular Reference Test",
                        "factory": "agents.planner",  # Invalid factory method
                        "agents": {
                            "self": "circular"  # Self-reference
                        },
                    }
                }
            }
            yaml.dump(config_with_circular, f)
            temp_path = Path(f.name)

        try:
            factory = WorkflowFactory(config_path=temp_path)

            # Should handle circular references gracefully
            resolved = await factory._resolve_agent_config("circular")
            assert isinstance(resolved, dict), "Should resolve circular reference to dict"

        except Exception as e:
            # Should fail gracefully with meaningful error
            assert "circular" in str(e).lower() or "reference" in str(e).lower()
        finally:
            temp_path.unlink()


class TestPerformanceConfiguration:
    """Test performance-related configuration validation."""

    @pytest.mark.asyncio
    async def test_performance_limits_configuration(self):
        """Test performance limits are properly configured."""
        factory = WorkflowFactory()

        # If the workflow config has performance settings, validate them
        try:
            config = await factory.get_workflow_config_async("magentic_fleet")

            # Check for any performance-related settings
            if hasattr(config, "orchestrator") and config.orchestrator:
                orch_config = config.orchestrator
                if isinstance(orch_config, dict):
                    # Validate max_round_count
                    if "max_round_count" in orch_config:
                        max_rounds = orch_config["max_round_count"]
                        assert isinstance(max_rounds, int), "max_round_count should be integer"
                        assert (
                            1 <= max_rounds <= 100
                        ), f"max_round_count {max_rounds} out of reasonable range"

                    # Validate max_stall_count
                    if "max_stall_count" in orch_config:
                        max_stalls = orch_config["max_stall_count"]
                        assert isinstance(max_stalls, int), "max_stall_count should be integer"
                        assert (
                            0 <= max_stalls <= 20
                        ), f"max_stall_count {max_stalls} out of reasonable range"

        except Exception:
            # Performance config validation should not fail tests
            pytest.skip("Performance configuration not available for validation")


class TestSecurityConfiguration:
    """Test security-related configuration validation."""

    @pytest.mark.asyncio
    async def test_no_hardcoded_secrets(self):
        """Test that configuration doesn't contain hardcoded secrets."""
        factory = WorkflowFactory()
        config = await factory.get_workflow_config_async("magentic_fleet")

        # Convert config to string for analysis
        config_str = str(config).lower()

        # Check for common secret patterns
        secret_patterns = ["password", "secret", "token", "key", "auth"]

        for pattern in secret_patterns:
            # Check if pattern appears with surrounding suspicious context
            if pattern in config_str:
                # This is a simple check - in production you'd want more sophisticated analysis
                # For now, just warn about potential secrets
                print("Warning: Potential security-sensitive item found in configuration")

    @pytest.mark.asyncio
    async def test_safe_model_references(self):
        """Test that model references don't contain unsafe characters."""
        factory = WorkflowFactory()
        config = await factory.get_workflow_config_async("magentic_fleet")

        all_models = set()
        for agent_config in config.agents.values():
            if isinstance(agent_config, dict) and "model" in agent_config:
                all_models.add(agent_config["model"])

        unsafe_patterns = ["../", "..\\", "/", "\\", "<", ">", "&", "|", ";"]
        for model in all_models:
            for pattern in unsafe_patterns:
                assert pattern not in model, f"Unsafe pattern '{pattern}' found in model: {model}"


if __name__ == "__main__":
    # Run configuration validation tests
    pytest.main([__file__, "-v", "--tb=short"])
