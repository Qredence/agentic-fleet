"""
Tests for Magentic Fleet Implementation

Verifies:
- MagenticFleet initialization with configuration
- Agent registration and participation
- Workflow execution with delegation
- Checkpoint integration
- HITL plan review integration
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agenticfleet.fleet.magentic_fleet import (
    NO_RESPONSE_GENERATED,
    MagenticFleet,
    create_default_fleet,
)


def test_fleet_builder_uses_workflow_defaults(monkeypatch):
    """Ensure workflow-level limits populate the Magentic builder when fleet config omits them."""
    from agenticfleet.fleet import fleet_builder as fb_module

    mock_settings = SimpleNamespace(
        workflow_config={
            "workflow": {"max_rounds": 7, "max_stalls": 4, "max_resets": 2},
            "fleet": {"manager": {}, "plan_review": {}, "callbacks": {}},
        },
        openai_model="test-model",
    )
    mock_settings.require_openai_api_key = lambda: "sk-test"

    monkeypatch.setattr(fb_module, "settings", mock_settings)

    builder = fb_module.FleetBuilder()

    assert builder.max_round_count == 7
    assert builder.max_stall_count == 4
    assert builder.max_reset_count == 2


@pytest.fixture
def mock_agents():
    """Create mock agents for testing."""
    researcher = MagicMock()
    researcher.name = "researcher"
    researcher.display_name = "Researcher"
    researcher.description = "Performs web searches"

    coder = MagicMock()
    coder.name = "coder"
    coder.display_name = "Coder"
    coder.description = "Writes and executes code"

    analyst = MagicMock()
    analyst.name = "analyst"
    analyst.display_name = "Analyst"
    analyst.description = "Analyzes data"

    return {
        "researcher": researcher,
        "coder": coder,
        "analyst": analyst,
    }


@pytest.fixture
def mock_workflow_runner():
    """Create a mock workflow runner."""
    runner = MagicMock()
    runner.run = AsyncMock()
    return runner


class TestMagenticFleetInitialization:
    """Test MagenticFleet initialization and configuration."""

    @patch("agenticfleet.fleet.magentic_fleet.create_researcher_agent")
    @patch("agenticfleet.fleet.magentic_fleet.create_coder_agent")
    @patch("agenticfleet.fleet.magentic_fleet.create_analyst_agent")
    @patch("agenticfleet.fleet.fleet_builder.FleetBuilder.build")
    def test_default_agent_creation(
        self,
        mock_build,
        mock_create_analyst,
        mock_create_coder,
        mock_create_researcher,
        mock_agents,
        mock_workflow_runner,
    ):
        """Test creating fleet with default agents."""
        # Setup mock agent factories
        mock_create_researcher.return_value = mock_agents["researcher"]
        mock_create_coder.return_value = mock_agents["coder"]
        mock_create_analyst.return_value = mock_agents["analyst"]
        mock_build.return_value = mock_workflow_runner

        # Create fleet (agents=None triggers default creation)
        fleet = MagenticFleet()

        # Verify all default agents were created
        mock_create_researcher.assert_called_once()
        mock_create_coder.assert_called_once()
        mock_create_analyst.assert_called_once()

        # Verify agents are stored
        assert len(fleet.agents) == 3
        assert "researcher" in fleet.agents
        assert "coder" in fleet.agents
        assert "analyst" in fleet.agents

    @patch("agenticfleet.fleet.fleet_builder.FleetBuilder.build")
    def test_custom_agent_initialization(self, mock_build, mock_agents, mock_workflow_runner):
        """Test fleet creation with custom agents."""
        mock_build.return_value = mock_workflow_runner

        # Create fleet with custom agents
        fleet = MagenticFleet(agents=mock_agents)

        # Verify custom agents were used
        assert fleet.agents == mock_agents
        assert len(fleet.agents) == 3

    @patch("agenticfleet.fleet.fleet_builder.FleetBuilder.build")
    def test_fleet_with_checkpoint_storage(self, mock_build, mock_agents, mock_workflow_runner):
        """Test fleet creation with checkpointing enabled."""
        mock_build.return_value = mock_workflow_runner

        # Mock checkpoint storage
        checkpoint_storage = MagicMock()

        # Create fleet with checkpointing
        fleet = MagenticFleet(
            agents=mock_agents,
            checkpoint_storage=checkpoint_storage,
        )

        # Verify checkpointing was configured
        assert fleet.checkpoint_storage == checkpoint_storage

    @patch("agenticfleet.fleet.fleet_builder.FleetBuilder.build")
    def test_fleet_with_approval_handler(self, mock_build, mock_agents, mock_workflow_runner):
        """Test fleet creation with HITL approval handler."""
        mock_build.return_value = mock_workflow_runner

        # Mock approval handler
        approval_handler = MagicMock()

        # Create fleet with plan review
        fleet = MagenticFleet(
            agents=mock_agents,
            approval_handler=approval_handler,
        )

        # Verify approval handler was configured
        assert fleet.approval_handler == approval_handler


class TestMagenticFleetExecution:
    """Test MagenticFleet workflow execution."""

    @patch("agenticfleet.fleet.fleet_builder.FleetBuilder.build")
    @pytest.mark.asyncio
    async def test_run_basic_task(self, mock_build, mock_agents, mock_workflow_runner):
        """Test running a basic task through the fleet."""
        mock_build.return_value = mock_workflow_runner

        # Mock workflow result
        mock_result = MagicMock()
        mock_result.output = "Task completed successfully"
        mock_workflow_runner.run.return_value = mock_result

        # Create and run fleet
        fleet = MagenticFleet(agents=mock_agents)
        result = await fleet.run("Search for Python best practices")

        # Verify execution
        assert result == "Task completed successfully"
        mock_workflow_runner.run.assert_called_once_with("Search for Python best practices")

    @patch("agenticfleet.fleet.fleet_builder.FleetBuilder.build")
    @pytest.mark.asyncio
    async def test_run_with_checkpoint_resume(self, mock_build, mock_agents, mock_workflow_runner):
        """Test resuming from a checkpoint."""
        mock_build.return_value = mock_workflow_runner

        # Mock workflow with checkpoint support
        mock_result = MagicMock()
        mock_result.output = "Resumed and completed"
        mock_workflow_runner.run.return_value = mock_result

        # Create fleet with checkpointing
        checkpoint_storage = MagicMock()
        fleet = MagenticFleet(
            agents=mock_agents,
            checkpoint_storage=checkpoint_storage,
        )

        # Run with checkpoint resume
        result = await fleet.run("Continue task", resume_from_checkpoint="test-checkpoint-123")

        # Verify execution (checkpoint restoration is handled internally)
        assert result == "Resumed and completed"
        mock_workflow_runner.run.assert_called_once_with(
            "Continue task", resume_from_checkpoint="test-checkpoint-123"
        )

    @patch("agenticfleet.fleet.fleet_builder.FleetBuilder.build")
    @pytest.mark.asyncio
    async def test_run_with_no_output(self, mock_build, mock_agents, mock_workflow_runner):
        """Test handling workflow with no output."""
        mock_build.return_value = mock_workflow_runner

        # Mock workflow result with no output and no content
        mock_result = MagicMock()
        mock_result.output = None
        mock_result.content = None  # Set content attribute to None
        mock_workflow_runner.run.return_value = mock_result

        # Create and run fleet
        fleet = MagenticFleet(agents=mock_agents)
        result = await fleet.run("Test task")

        # Verify fallback message
        assert result == NO_RESPONSE_GENERATED

    @patch("agenticfleet.fleet.fleet_builder.FleetBuilder.build")
    @pytest.mark.asyncio
    async def test_run_with_output_none_content_value(
        self, mock_build, mock_agents, mock_workflow_runner
    ):
        """Test handling workflow with output None but content has a value."""
        mock_build.return_value = mock_workflow_runner

        # Mock workflow result with output None, content has value
        mock_result = MagicMock()
        mock_result.output = None
        mock_result.content = "Content fallback value"
        mock_workflow_runner.run.return_value = mock_result

        fleet = MagenticFleet(agents=mock_agents)
        result = await fleet.run("Test task")

        # Should fallback to content value
        assert result == "Content fallback value"

    @patch("agenticfleet.fleet.fleet_builder.FleetBuilder.build")
    @pytest.mark.asyncio
    async def test_run_with_output_value_content_none(
        self, mock_build, mock_agents, mock_workflow_runner
    ):
        """Test handling workflow with output has value but content is None."""
        mock_build.return_value = mock_workflow_runner

        # Mock workflow result with output has value, content is None
        mock_result = MagicMock()
        mock_result.output = "Output value"
        mock_result.content = None
        mock_workflow_runner.run.return_value = mock_result

        fleet = MagenticFleet(agents=mock_agents)
        result = await fleet.run("Test task")

        # Should use output value
        assert result == "Output value"

    @patch("agenticfleet.fleet.fleet_builder.FleetBuilder.build")
    @pytest.mark.asyncio
    async def test_workflow_id_generation(self, mock_build, mock_agents, mock_workflow_runner):
        """Test automatic workflow ID generation."""
        mock_build.return_value = mock_workflow_runner

        mock_result = MagicMock()
        mock_result.output = "Done"
        mock_workflow_runner.run.return_value = mock_result

        # Create fleet without setting workflow ID
        fleet = MagenticFleet(agents=mock_agents)
        assert fleet.workflow_id is None

        # Run workflow (should generate ID)
        await fleet.run("Test task")

        # Verify ID was generated
        assert fleet.workflow_id is not None
        assert fleet.workflow_id.startswith("fleet_")

    @patch("agenticfleet.fleet.fleet_builder.FleetBuilder.build")
    @pytest.mark.asyncio
    async def test_set_workflow_id(self, mock_build, mock_agents, mock_workflow_runner):
        """Test manually setting workflow ID."""
        mock_build.return_value = mock_workflow_runner

        # Create fleet and set ID
        fleet = MagenticFleet(agents=mock_agents)
        fleet.set_workflow_id("custom-workflow-123")

        # Verify ID was set
        assert fleet.workflow_id == "custom-workflow-123"


class TestMagenticFleetFactoryMethod:
    """Test create_default_fleet factory method."""

    @patch("agenticfleet.fleet.magentic_fleet.create_researcher_agent")
    @patch("agenticfleet.fleet.magentic_fleet.create_coder_agent")
    @patch("agenticfleet.fleet.magentic_fleet.create_analyst_agent")
    @patch("agenticfleet.fleet.magentic_fleet.set_approval_handler")
    @patch("agenticfleet.fleet.magentic_fleet.settings.create_checkpoint_storage")
    @patch("agenticfleet.fleet.fleet_builder.FleetBuilder.build")
    def test_create_default_fleet(
        self,
        mock_build,
        mock_create_checkpoint,
        mock_set_handler,
        mock_create_analyst,
        mock_create_coder,
        mock_create_researcher,
        mock_agents,
        mock_workflow_runner,
    ):
        """Test creating fleet with factory method."""
        # Setup mocks
        mock_create_researcher.return_value = mock_agents["researcher"]
        mock_create_coder.return_value = mock_agents["coder"]
        mock_create_analyst.return_value = mock_agents["analyst"]
        mock_create_checkpoint.return_value = MagicMock()
        mock_build.return_value = mock_workflow_runner

        # Create default fleet
        fleet = create_default_fleet()

        # Verify agents were created
        mock_create_researcher.assert_called_once()
        mock_create_coder.assert_called_once()
        mock_create_analyst.assert_called_once()

        # Verify checkpoint storage was created
        mock_create_checkpoint.assert_called_once()
        mock_set_handler.assert_called_once()
        handler_arg = mock_set_handler.call_args.args[0]
        assert handler_arg is not None
        call_kwargs = mock_set_handler.call_args.kwargs
        assert "require_operations" in call_kwargs
        assert "trusted_operations" in call_kwargs

        # Verify fleet is properly initialized
        assert fleet is not None
        assert len(fleet.agents) == 3


class TestMagenticFleetBuilder:
    """Test FleetBuilder configuration."""

    @patch("agenticfleet.fleet.fleet_builder.MagenticBuilder")
    def test_builder_fluent_api(self, mock_magentic_builder_class, mock_agents):
        """Test FleetBuilder fluent API."""
        from agenticfleet.fleet.fleet_builder import FleetBuilder

        # Setup
        mock_magentic_builder = MagicMock()
        mock_magentic_builder_class.return_value = mock_magentic_builder
        mock_magentic_builder.build.return_value = MagicMock()

        # Create builder and chain configuration
        builder = FleetBuilder()
        result = (
            builder.with_agents(mock_agents)
            .with_manager()
            .with_observability()
            .with_checkpointing(MagicMock())
            .with_plan_review()
        )

        # Verify fluent API returns self
        assert result == builder


class TestMagenticFleetCallbacks:
    """Test Magentic Fleet event callbacks."""

    @pytest.mark.asyncio
    async def test_streaming_agent_response_callback(self):
        """Test streaming agent response callback."""
        from agenticfleet.fleet.callbacks import ConsoleCallbacks

        # Mock message with agent_name and content attributes
        message = MagicMock()
        message.agent_name = "researcher"
        message.content = "Response chunk from researcher"

        # Call callback (should not raise)
        handlers = ConsoleCallbacks()
        await handlers.agent_delta_callback(message)

        # If we get here, callback succeeded
        assert True

    @pytest.mark.asyncio
    async def test_plan_creation_callback(self):
        """Test plan creation callback."""
        from agenticfleet.fleet.callbacks import ConsoleCallbacks

        # Mock plan
        plan = MagicMock()
        plan.steps = ["Step 1", "Step 2"]

        # Call callback (should not raise)
        handlers = ConsoleCallbacks()
        await handlers.plan_creation_callback(plan)
        assert True

    @pytest.mark.asyncio
    async def test_progress_ledger_callback(self):
        """Test progress ledger callback."""
        from agenticfleet.fleet.callbacks import ConsoleCallbacks

        # Mock ledger
        ledger = MagicMock()

        # Call callback (should not raise)
        handlers = ConsoleCallbacks()
        await handlers.progress_ledger_callback(ledger)
        assert True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
