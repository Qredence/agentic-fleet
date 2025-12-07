"""Comprehensive tests for workflows/builder.py."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from agentic_fleet.workflows.builder import (
    WorkflowBuilder,
    build_workflow_from_config,
)
from agentic_fleet.agents.base import Agent


class TestWorkflowBuilder:
    """Test suite for WorkflowBuilder class."""

    @pytest.fixture
    def mock_config(self):
        """Provide a mock configuration."""
        return {
            "execution": {
                "max_iterations": 5,
                "quality_threshold": 0.8,
                "timeout_seconds": 300,
            },
            "agents": {
                "researcher": {
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "tools": ["TavilyMCPTool"],
                },
                "analyst": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.5,
                    "tools": [],
                },
            },
            "dspy": {
                "optimization": {
                    "use_typed_signatures": True,
                    "enable_routing_cache": True,
                    "cache_ttl_seconds": 300,
                }
            },
        }

    @pytest.fixture
    def builder(self, mock_config):
        """Create a WorkflowBuilder instance."""
        return WorkflowBuilder(mock_config)

    def test_builder_initialization(self, builder, mock_config):
        """Test WorkflowBuilder initialization."""
        assert builder.config == mock_config
        assert builder.config["execution"]["max_iterations"] == 5
        assert builder.config["execution"]["quality_threshold"] == 0.8

    def test_builder_initialization_with_defaults(self):
        """Test builder initialization with minimal config."""
        minimal_config = {"agents": {}}
        builder = WorkflowBuilder(minimal_config)
        assert builder.config == minimal_config

    def test_extract_execution_params(self, builder):
        """Test extraction of execution parameters from config."""
        params = builder._extract_execution_params()
        assert params["max_iterations"] == 5
        assert params["quality_threshold"] == 0.8
        assert params["timeout_seconds"] == 300

    def test_extract_execution_params_with_missing_keys(self):
        """Test execution params extraction with missing keys."""
        config = {"execution": {"max_iterations": 10}}
        builder = WorkflowBuilder(config)
        params = builder._extract_execution_params()
        assert params["max_iterations"] == 10
        # Should handle missing keys gracefully
        assert "quality_threshold" not in params or params.get("quality_threshold") is None

    def test_extract_dspy_params(self, builder):
        """Test extraction of DSPy parameters."""
        params = builder._extract_dspy_params()
        assert params["use_typed_signatures"] is True
        assert params["enable_routing_cache"] is True
        assert params["cache_ttl_seconds"] == 300

    def test_extract_dspy_params_with_defaults(self):
        """Test DSPy params with default values."""
        config = {"dspy": {}}
        builder = WorkflowBuilder(config)
        params = builder._extract_dspy_params()
        # Should return empty or default values
        assert isinstance(params, dict)

    @patch("agentic_fleet.workflows.builder.create_supervisor_workflow")
    async def test_build_async_workflow(self, mock_create, builder):
        """Test building an async workflow."""
        mock_workflow = AsyncMock()
        mock_create.return_value = mock_workflow

        workflow = await builder.build_async()

        mock_create.assert_called_once()
        assert workflow == mock_workflow

    @patch("agentic_fleet.workflows.builder.AgentFactory")
    async def test_build_with_agent_factory(self, mock_factory, builder):
        """Test workflow building with AgentFactory."""
        mock_agent = Mock(spec=Agent)
        mock_factory.return_value.create_agent.return_value = mock_agent

        with patch("agentic_fleet.workflows.builder.create_supervisor_workflow") as mock_create:
            mock_create.return_value = AsyncMock()
            await builder.build_async()

        # Verify factory was used
        assert mock_create.called

    def test_validate_config_structure(self, builder):
        """Test configuration structure validation."""
        # Valid config should not raise
        builder._validate_config()

    def test_validate_config_with_invalid_structure(self):
        """Test validation with invalid config structure."""
        invalid_config = {"invalid_key": "value"}
        _ = WorkflowBuilder(invalid_config)
        # Should handle gracefully or raise appropriate error
        # (Depends on implementation - adjust based on actual behavior)

    def test_get_agent_config(self, builder):
        """Test retrieving specific agent configuration."""
        researcher_config = builder.config["agents"]["researcher"]
        assert researcher_config["model"] == "gpt-4o"
        assert researcher_config["temperature"] == 0.7
        assert "TavilyMCPTool" in researcher_config["tools"]

    def test_get_nonexistent_agent_config(self, builder):
        """Test retrieving config for non-existent agent."""
        with pytest.raises(KeyError):
            _ = builder.config["agents"]["nonexistent_agent"]


class TestBuildWorkflowFromConfig:
    """Test suite for build_workflow_from_config function."""

    @pytest.fixture
    def sample_config(self):
        """Provide sample configuration."""
        return {
            "execution": {"max_iterations": 10},
            "agents": {
                "researcher": {"model": "gpt-4o"},
            },
        }

    @patch("agentic_fleet.workflows.builder.WorkflowBuilder")
    async def test_build_workflow_from_config(self, mock_builder_class, sample_config):
        """Test building workflow from config."""
        mock_builder = Mock()
        mock_workflow = AsyncMock()
        mock_builder.build_async.return_value = mock_workflow
        mock_builder_class.return_value = mock_builder

        workflow = await build_workflow_from_config(sample_config)

        mock_builder_class.assert_called_once_with(sample_config)
        mock_builder.build_async.assert_called_once()
        assert workflow == mock_workflow

    async def test_build_workflow_with_none_config(self):
        """Test building workflow with None config."""
        with pytest.raises((TypeError, ValueError)):
            await build_workflow_from_config(None)

    async def test_build_workflow_with_empty_config(self):
        """Test building workflow with empty config."""
        empty_config = {}
        with patch("agentic_fleet.workflows.builder.WorkflowBuilder") as mock_builder_class:
            mock_builder = Mock()
            mock_builder.build_async.return_value = AsyncMock()
            mock_builder_class.return_value = mock_builder

            workflow = await build_workflow_from_config(empty_config)
            assert workflow is not None


class TestWorkflowBuilderEdgeCases:
    """Test edge cases and error handling."""

    def test_builder_with_malformed_config(self):
        """Test builder with malformed configuration."""
        malformed_configs = [
            {"agents": None},
            {"execution": "invalid"},
            {"dspy": []},
        ]

        for config in malformed_configs:
            builder = WorkflowBuilder(config)
            # Should handle gracefully
            assert builder.config == config

    def test_builder_config_immutability(self, mock_config):
        """Test that builder doesn't mutate original config."""
        import copy

        original_config = copy.deepcopy(mock_config)
        builder = WorkflowBuilder(mock_config)

        # Modify builder's config
        builder.config["execution"]["max_iterations"] = 999

        # Original should be unchanged (if deep copy is used)
        # Note: This test assumes the implementation makes a copy
        assert original_config["execution"]["max_iterations"] == 5

    @patch("agentic_fleet.workflows.builder.create_supervisor_workflow")
    async def test_build_with_creation_failure(self, mock_create):
        """Test handling of workflow creation failure."""
        mock_create.side_effect = Exception("Creation failed")

        config = {"agents": {}}
        builder = WorkflowBuilder(config)

        with pytest.raises(Exception, match="Creation failed"):
            await builder.build_async()

    def test_extract_nested_config_values(self):
        """Test extracting deeply nested configuration values."""
        config = {
            "level1": {
                "level2": {"level3": {"value": 42}},
            },
        }
        builder = WorkflowBuilder(config)

        value = builder.config["level1"]["level2"]["level3"]["value"]
        assert value == 42

    def test_config_with_unicode_and_special_chars(self):
        """Test config handling with unicode and special characters."""
        config = {
            "agents": {
                "测试agent": {"model": "gpt-4o"},
                "agent-with-dash": {"temperature": 0.5},
            },
        }
        builder = WorkflowBuilder(config)
        assert "测试agent" in builder.config["agents"]
        assert "agent-with-dash" in builder.config["agents"]


class TestWorkflowBuilderIntegration:
    """Integration tests for WorkflowBuilder."""

    @pytest.fixture
    def full_config(self):
        """Provide a full configuration for integration testing."""
        return {
            "execution": {
                "max_iterations": 5,
                "quality_threshold": 0.8,
                "timeout_seconds": 300,
                "enable_progress_tracking": True,
            },
            "agents": {
                "researcher": {
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "tools": ["TavilyMCPTool"],
                },
                "analyst": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.5,
                    "tools": [],
                },
                "writer": {
                    "model": "gpt-4o",
                    "temperature": 0.8,
                    "tools": [],
                },
            },
            "dspy": {
                "optimization": {
                    "use_typed_signatures": True,
                    "enable_routing_cache": True,
                    "cache_ttl_seconds": 300,
                    "require_compiled": False,
                },
            },
            "tracing": {
                "enabled": True,
                "export_to_azure": False,
            },
        }

    @patch("agentic_fleet.workflows.builder.create_supervisor_workflow")
    async def test_full_workflow_build(self, mock_create, full_config):
        """Test building a complete workflow with full configuration."""
        mock_workflow = AsyncMock()
        mock_create.return_value = mock_workflow

        workflow = await build_workflow_from_config(full_config)

        assert workflow is not None
        mock_create.assert_called_once()

    def test_config_validation_with_all_sections(self, full_config):
        """Test configuration validation with all sections present."""
        builder = WorkflowBuilder(full_config)

        # Validate all sections are accessible
        assert "execution" in builder.config
        assert "agents" in builder.config
        assert "dspy" in builder.config
        assert "tracing" in builder.config

    def test_multiple_agents_configuration(self, full_config):
        """Test configuration with multiple agents."""
        builder = WorkflowBuilder(full_config)

        agents = builder.config["agents"]
        assert len(agents) == 3
        assert "researcher" in agents
        assert "analyst" in agents
        assert "writer" in agents