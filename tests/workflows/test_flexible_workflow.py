"""Tests for flexible workflow builder and integration."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.dspy_modules.reasoner import DSPyReasoner
from agentic_fleet.workflows.builder import build_fleet_workflow
from agentic_fleet.workflows.context import SupervisorContext
from agentic_fleet.workflows.supervisor import create_supervisor_workflow


@pytest.fixture
def mock_supervisor():
    supervisor = MagicMock(spec=DSPyReasoner)
    supervisor.tool_registry = MagicMock()
    return supervisor


@pytest.fixture
def mock_context(mock_supervisor):
    context = MagicMock(spec=SupervisorContext)
    context.dspy_supervisor = mock_supervisor
    context.agents = {}
    context.tool_registry = MagicMock()
    context.config = MagicMock()  # Add config
    return context


def test_build_flexible_workflow_standard(mock_supervisor, mock_context):
    """Test building standard workflow."""
    builder = build_fleet_workflow(mock_supervisor, mock_context, mode="standard")
    assert builder is not None
    # In standard mode, it returns a WorkflowBuilder (or compatible object)
    # We can check if it has expected methods or type
    assert hasattr(builder, "set_start_executor") or hasattr(builder, "add_edge")


def test_build_flexible_workflow_group_chat(mock_supervisor, mock_context):
    """Test building group chat workflow."""
    builder = build_fleet_workflow(mock_supervisor, mock_context, mode="group_chat")
    assert builder is not None
    # In group chat mode, it returns a GroupChatBuilder
    assert hasattr(builder, "participants")


@pytest.mark.asyncio
async def test_create_fleet_workflow_modes(mock_context):
    """Test create_supervisor_workflow with different modes."""

    # Test standard mode
    workflow_standard = await create_supervisor_workflow(
        context=mock_context, mode="standard", compile_dspy=False
    )
    assert workflow_standard is not None

    # Test group chat mode
    # We need to patch the builder to avoid actual agent creation issues if dependencies are missing
    with patch("agentic_fleet.workflows.builder._build_group_chat_workflow") as mock_build:
        mock_build.return_value.build.return_value = MagicMock()

        # Mock initialization since we are testing modes not initialization
        with patch("agentic_fleet.workflows.supervisor.initialize_workflow_context") as mock_init:
            mock_init.return_value = mock_context
            workflow_gc = await create_supervisor_workflow(mode="group_chat", compile_dspy=False)
            assert workflow_gc is not None
            mock_build.assert_called_once()
