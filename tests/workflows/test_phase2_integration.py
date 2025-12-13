"""Tests for Phase 2: Integration of decision modules into workflow execution paths.

This module tests that preloaded decision modules from app.state are properly
injected into the DSPyReasoner and used by workflow executors.
"""

from unittest.mock import MagicMock

import pytest

from agentic_fleet.dspy_modules.reasoner import DSPyReasoner
from agentic_fleet.workflows.context import SupervisorContext
from agentic_fleet.workflows.supervisor import create_supervisor_workflow


class TestDecisionModuleInjection:
    """Test decision module injection into DSPy reasoner."""

    def test_dspy_reasoner_accepts_decision_modules(self):
        """Test that DSPyReasoner has set_decision_modules method."""
        reasoner = DSPyReasoner()
        assert hasattr(reasoner, "set_decision_modules")
        assert callable(reasoner.set_decision_modules)

    def test_set_decision_modules_injects_routing_module(self):
        """Test that routing module is properly injected."""
        reasoner = DSPyReasoner()
        mock_routing_module = MagicMock()

        reasoner.set_decision_modules(routing_module=mock_routing_module)

        assert reasoner._router is mock_routing_module

    def test_set_decision_modules_injects_quality_module(self):
        """Test that quality module is properly injected."""
        reasoner = DSPyReasoner()
        mock_quality_module = MagicMock()

        reasoner.set_decision_modules(quality_module=mock_quality_module)

        assert reasoner._quality_assessor is mock_quality_module

    def test_set_decision_modules_injects_tool_planning_module(self):
        """Test that tool planning module is properly injected."""
        reasoner = DSPyReasoner()
        mock_tool_planning_module = MagicMock()

        reasoner.set_decision_modules(tool_planning_module=mock_tool_planning_module)

        assert reasoner._tool_planner is mock_tool_planning_module

    def test_set_decision_modules_injects_all_modules(self):
        """Test that all decision modules can be injected at once."""
        reasoner = DSPyReasoner()
        mock_routing = MagicMock()
        mock_quality = MagicMock()
        mock_tool_planning = MagicMock()

        reasoner.set_decision_modules(
            routing_module=mock_routing,
            quality_module=mock_quality,
            tool_planning_module=mock_tool_planning,
        )

        assert reasoner._router is mock_routing
        assert reasoner._quality_assessor is mock_quality
        assert reasoner._tool_planner is mock_tool_planning

    def test_set_decision_modules_accepts_none_values(self):
        """Test that None values don't overwrite existing modules."""
        reasoner = DSPyReasoner()
        # Initialize modules first
        reasoner._ensure_modules_initialized()
        original_router = reasoner._router

        # Call with None values
        reasoner.set_decision_modules(
            routing_module=None, quality_module=None, tool_planning_module=None
        )

        # Original module should be unchanged
        assert reasoner._router is original_router


class TestSupervisorContextDecisionModules:
    """Test SupervisorContext holds decision module references."""

    def test_supervisor_context_has_decision_module_fields(self):
        """Test that SupervisorContext has decision module fields."""
        from agentic_fleet.workflows.config import WorkflowConfig

        context = SupervisorContext(config=WorkflowConfig())
        assert hasattr(context, "dspy_routing_module")
        assert hasattr(context, "dspy_quality_module")
        assert hasattr(context, "dspy_tool_planning_module")

    def test_supervisor_context_decision_modules_default_to_none(self):
        """Test that decision module fields default to None."""
        from agentic_fleet.workflows.config import WorkflowConfig

        context = SupervisorContext(config=WorkflowConfig())
        assert context.dspy_routing_module is None
        assert context.dspy_quality_module is None
        assert context.dspy_tool_planning_module is None

    def test_supervisor_context_can_hold_decision_modules(self):
        """Test that decision modules can be assigned to context."""
        from agentic_fleet.workflows.config import WorkflowConfig

        context = SupervisorContext(config=WorkflowConfig())
        mock_routing = MagicMock()
        mock_quality = MagicMock()
        mock_tool_planning = MagicMock()

        context.dspy_routing_module = mock_routing
        context.dspy_quality_module = mock_quality
        context.dspy_tool_planning_module = mock_tool_planning

        assert context.dspy_routing_module is mock_routing
        assert context.dspy_quality_module is mock_quality
        assert context.dspy_tool_planning_module is mock_tool_planning


class TestWorkflowDecisionModuleIntegration:
    """Test workflow initialization with decision modules."""

    @pytest.mark.asyncio
    async def test_create_supervisor_workflow_accepts_decision_modules(self):
        """Test that create_supervisor_workflow accepts decision module parameters."""
        from agentic_fleet.workflows.config import WorkflowConfig

        # Create a pre-initialized context to avoid environment validation
        mock_context = SupervisorContext(
            config=WorkflowConfig(),
            dspy_supervisor=DSPyReasoner(),
        )

        mock_routing = MagicMock()
        mock_quality = MagicMock()
        mock_tool_planning = MagicMock()

        # This should not raise any errors
        workflow = await create_supervisor_workflow(
            context=mock_context,
            dspy_routing_module=mock_routing,
            dspy_quality_module=mock_quality,
            dspy_tool_planning_module=mock_tool_planning,
        )

        # Verify modules were attached to context
        assert workflow.context.dspy_routing_module is mock_routing
        assert workflow.context.dspy_quality_module is mock_quality
        assert workflow.context.dspy_tool_planning_module is mock_tool_planning

    @pytest.mark.asyncio
    async def test_create_supervisor_workflow_injects_modules_to_reasoner(self):
        """Test that decision modules are injected into DSPy reasoner."""
        from agentic_fleet.workflows.config import WorkflowConfig

        # Create a pre-initialized context to avoid environment validation
        mock_context = SupervisorContext(
            config=WorkflowConfig(),
            dspy_supervisor=DSPyReasoner(),
        )

        mock_routing = MagicMock()
        mock_quality = MagicMock()
        mock_tool_planning = MagicMock()

        workflow = await create_supervisor_workflow(
            context=mock_context,
            dspy_routing_module=mock_routing,
            dspy_quality_module=mock_quality,
            dspy_tool_planning_module=mock_tool_planning,
        )

        # Verify modules were injected into reasoner
        assert workflow.context.dspy_supervisor is not None
        reasoner = workflow.context.dspy_supervisor
        assert reasoner._router is mock_routing
        assert reasoner._quality_assessor is mock_quality
        assert reasoner._tool_planner is mock_tool_planning

    @pytest.mark.asyncio
    async def test_create_supervisor_workflow_without_modules(self):
        """Test that workflow creation works without decision modules (backward compat)."""
        from agentic_fleet.workflows.config import WorkflowConfig

        # Create a pre-initialized context to avoid environment validation
        mock_context = SupervisorContext(
            config=WorkflowConfig(),
            dspy_supervisor=DSPyReasoner(),
        )

        # This should not raise any errors and should use default modules
        workflow = await create_supervisor_workflow(context=mock_context)

        # Verify workflow is created successfully
        assert workflow is not None
        assert workflow.context is not None
        assert workflow.context.dspy_supervisor is not None

    @pytest.mark.asyncio
    async def test_create_supervisor_workflow_partial_modules(self):
        """Test workflow creation with only some decision modules provided."""
        from agentic_fleet.workflows.config import WorkflowConfig

        # Create a pre-initialized context to avoid environment validation
        mock_context = SupervisorContext(
            config=WorkflowConfig(),
            dspy_supervisor=DSPyReasoner(),
        )

        mock_quality = MagicMock()

        workflow = await create_supervisor_workflow(
            context=mock_context, dspy_quality_module=mock_quality
        )

        # Verify only quality module was injected
        assert workflow.context.dspy_quality_module is mock_quality
        assert workflow.context.dspy_routing_module is None
        assert workflow.context.dspy_tool_planning_module is None
