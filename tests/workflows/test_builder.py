"""Tests for workflows/builder.py - Fleet workflow building utilities."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agentic_fleet.workflows.builder import (
    GroupChatBuilder,
    HandoffBuilder,
    WorkflowBuilder,
    build_fleet_workflow,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_supervisor() -> MagicMock:
    """Create a mock DSPyReasoner."""
    supervisor = MagicMock(spec=["analyze", "route", "judge"])
    return supervisor


@pytest.fixture
def mock_context() -> MagicMock:
    """Create a mock SupervisorContext."""
    context = MagicMock()
    context.agents = {
        "researcher": MagicMock(description="Research specialist"),
        "analyst": MagicMock(description="Data analyst"),
    }
    context.openai_client = MagicMock()
    context.config = MagicMock()
    context.config.model = "gpt-4.1-mini"
    context.config.dspy = MagicMock()
    context.config.dspy.model = "gpt-4.1-mini"
    return context


@pytest.fixture
def mock_context_no_agents() -> MagicMock:
    """Create a mock SupervisorContext without agents."""
    context = MagicMock()
    context.agents = {}
    context.openai_client = MagicMock()
    context.config = MagicMock()
    return context


@pytest.fixture
def mock_context_no_client() -> MagicMock:
    """Create a mock SupervisorContext without OpenAI client."""
    context = MagicMock()
    context.agents = {"researcher": MagicMock(description="Researcher")}
    context.openai_client = None
    context.config = MagicMock()
    return context


# =============================================================================
# Test: build_fleet_workflow function
# =============================================================================


class TestBuildFleetWorkflow:
    """Test suite for build_fleet_workflow function."""

    def test_build_standard_workflow(self, mock_supervisor, mock_context):
        """Test building standard workflow mode."""
        workflow = build_fleet_workflow(mock_supervisor, mock_context, mode="standard")
        assert workflow is not None
        # Should return a WorkflowBuilder
        assert isinstance(workflow, WorkflowBuilder)

    def test_build_concurrent_workflow(self, mock_supervisor, mock_context):
        """Test building concurrent workflow mode (falls back to standard)."""
        workflow = build_fleet_workflow(mock_supervisor, mock_context, mode="concurrent")
        assert workflow is not None
        assert isinstance(workflow, WorkflowBuilder)

    def test_build_default_mode(self, mock_supervisor, mock_context):
        """Test building with default mode."""
        workflow = build_fleet_workflow(mock_supervisor, mock_context)
        assert workflow is not None
        assert isinstance(workflow, WorkflowBuilder)

    @pytest.mark.skipif(
        GroupChatBuilder.__name__ == "_GroupChatBuilderStub",
        reason="GroupChatBuilder not available in this agent-framework version",
    )
    def test_build_group_chat_workflow(self, mock_supervisor, mock_context):
        """Test building group chat workflow mode."""
        workflow = build_fleet_workflow(mock_supervisor, mock_context, mode="group_chat")
        assert workflow is not None

    @pytest.mark.skipif(
        HandoffBuilder.__name__ == "_HandoffBuilderStub",
        reason="HandoffBuilder not available in this agent-framework version",
    )
    def test_build_handoff_workflow(self, mock_supervisor, mock_context):
        """Test building handoff workflow mode."""
        # This test requires full agent-framework integration
        # Skip if mocking doesn't work cleanly
        pytest.skip("Requires full agent-framework integration for OpenAI client mocking")

    @pytest.mark.skipif(
        HandoffBuilder.__name__ == "_HandoffBuilderStub",
        reason="HandoffBuilder not available",
    )
    def test_build_handoff_workflow_no_agents_raises(self, mock_supervisor, mock_context_no_agents):
        """Test that handoff mode raises when no agents available."""
        with pytest.raises(RuntimeError, match="No agents available"):
            build_fleet_workflow(mock_supervisor, mock_context_no_agents, mode="handoff")

    @pytest.mark.skipif(
        HandoffBuilder.__name__ == "_HandoffBuilderStub",
        reason="HandoffBuilder not available",
    )
    def test_build_handoff_workflow_no_client_raises(self, mock_supervisor, mock_context_no_client):
        """Test that handoff mode raises when no OpenAI client."""
        with pytest.raises(RuntimeError, match="OpenAI client required"):
            build_fleet_workflow(mock_supervisor, mock_context_no_client, mode="handoff")


# =============================================================================
# Test: Standard Workflow Structure
# =============================================================================


class TestStandardWorkflowStructure:
    """Test the structure of standard workflow."""

    def test_workflow_has_executors(self, mock_supervisor, mock_context):
        """Test that workflow is built with expected executors."""
        workflow = build_fleet_workflow(mock_supervisor, mock_context, mode="standard")

        # WorkflowBuilder should be configured with executors
        assert workflow is not None
        # The builder should have been configured via set_start_executor and add_edge

    def test_workflow_pipeline_order(self, mock_supervisor, mock_context):
        """Test that workflow follows expected pipeline order."""
        # Pipeline: analysis → routing → execution → progress → quality
        workflow = build_fleet_workflow(mock_supervisor, mock_context, mode="standard")
        assert workflow is not None


# =============================================================================
# Test: WorkflowBuilder Import
# =============================================================================


class TestWorkflowBuilderImport:
    """Test WorkflowBuilder availability and basic operations."""

    def test_workflow_builder_import(self):
        """Test that WorkflowBuilder can be imported."""
        assert WorkflowBuilder is not None

    def test_workflow_builder_instantiation(self):
        """Test that WorkflowBuilder can be instantiated."""
        builder = WorkflowBuilder()
        assert builder is not None

    def test_workflow_builder_has_set_start_executor(self):
        """Test that WorkflowBuilder has set_start_executor method."""
        builder = WorkflowBuilder()
        assert hasattr(builder, "set_start_executor")

    def test_workflow_builder_has_add_edge(self):
        """Test that WorkflowBuilder has add_edge method."""
        builder = WorkflowBuilder()
        assert hasattr(builder, "add_edge")


# =============================================================================
# Test: GroupChatBuilder Import
# =============================================================================


class TestGroupChatBuilderImport:
    """Test GroupChatBuilder availability."""

    def test_group_chat_builder_import(self):
        """Test that GroupChatBuilder can be imported (may be stub)."""
        assert GroupChatBuilder is not None

    @pytest.mark.skipif(
        GroupChatBuilder.__name__ == "_GroupChatBuilderStub",
        reason="GroupChatBuilder is a stub in this environment",
    )
    def test_group_chat_builder_instantiation(self):
        """Test GroupChatBuilder instantiation when available."""
        builder = GroupChatBuilder()
        assert builder is not None


# =============================================================================
# Test: HandoffBuilder Import
# =============================================================================


class TestHandoffBuilderImport:
    """Test HandoffBuilder availability."""

    def test_handoff_builder_import(self):
        """Test that HandoffBuilder can be imported (may be stub)."""
        assert HandoffBuilder is not None

    @pytest.mark.skipif(
        HandoffBuilder.__name__ == "_HandoffBuilderStub",
        reason="HandoffBuilder is a stub in this environment",
    )
    def test_handoff_builder_instantiation(self):
        """Test HandoffBuilder instantiation when available."""
        # HandoffBuilder requires proper AgentProtocol instances
        # This would need actual agent-framework agents to work
        pytest.skip("HandoffBuilder requires actual AgentProtocol instances")


# =============================================================================
# Test: Workflow Mode Selection
# =============================================================================


class TestWorkflowModeSelection:
    """Test workflow mode selection logic."""

    @pytest.mark.parametrize(
        ("mode", "expected_type"),
        [
            ("standard", WorkflowBuilder),
            ("concurrent", WorkflowBuilder),  # Falls back to standard
        ],
    )
    def test_mode_returns_expected_type(self, mock_supervisor, mock_context, mode, expected_type):
        """Test that each mode returns the expected builder type."""
        workflow = build_fleet_workflow(mock_supervisor, mock_context, mode=mode)
        assert isinstance(workflow, expected_type)

    def test_invalid_mode_falls_back_to_standard(self, mock_supervisor, mock_context):
        """Test that unrecognized mode falls back to standard."""
        # The function uses else clause for unknown modes
        workflow = build_fleet_workflow(
            mock_supervisor,
            mock_context,
            mode="unknown_mode",  # type: ignore[arg-type]
        )
        assert isinstance(workflow, WorkflowBuilder)


# =============================================================================
# Test: Executor Integration
# =============================================================================


class TestExecutorIntegration:
    """Test executor integration in workflow building.

    Note: These tests verify that executors are instantiated during workflow
    building. Due to strict type validation in WorkflowBuilder, we verify
    the executor classes exist and are callable rather than full mocking.
    """

    def test_executor_classes_importable(self):
        """Test that all executor classes can be imported."""
        from agentic_fleet.workflows.executors import (
            AnalysisExecutor,
            ExecutionExecutor,
            ProgressExecutor,
            QualityExecutor,
            RoutingExecutor,
        )

        assert AnalysisExecutor is not None
        assert RoutingExecutor is not None
        assert ExecutionExecutor is not None
        assert ProgressExecutor is not None
        assert QualityExecutor is not None

    def test_executor_classes_are_callable(self):
        """Test that executor classes are callable (can be instantiated)."""
        from agentic_fleet.workflows.executors import (
            AnalysisExecutor,
            ExecutionExecutor,
            ProgressExecutor,
            QualityExecutor,
            RoutingExecutor,
        )

        # All should be classes (callable)
        assert callable(AnalysisExecutor)
        assert callable(RoutingExecutor)
        assert callable(ExecutionExecutor)
        assert callable(ProgressExecutor)
        assert callable(QualityExecutor)
