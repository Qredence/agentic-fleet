from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_fleet.dspy_modules.supervisor import DSPySupervisor
from agentic_fleet.utils.models import ExecutionMode
from agentic_fleet.workflows.fleet.adapter import SupervisorWorkflow


@pytest.mark.asyncio
async def test_workflow_synergy_sequential_execution():
    """Test the flow from Analysis -> Routing (Sequential) -> Execution."""

    # Mock DSPySupervisor
    mock_supervisor = MagicMock(spec=DSPySupervisor)

    # Mock Analysis
    mock_supervisor.analyze_task.return_value = {
        "complexity": "medium",
        "required_capabilities": ["research", "analysis"],
    }

    # Mock Routing (Sequential)
    mock_supervisor.route_task.return_value = {
        "task": "Test Task",
        "assigned_to": ["Researcher", "Analyst"],
        "mode": ExecutionMode.SEQUENTIAL.value,
        "subtasks": ["Research X", "Analyze Y"],
    }

    # Mock Tool Planning (ReAct-style)
    mock_supervisor.decide_tools.return_value = {"tool_plan": ["tavily_search", "code_interpreter"]}

    # Mock Quality Assessment
    mock_supervisor.assess_quality.return_value = {"score": 9.0, "missing": "", "improvements": ""}

    # Mock Agents
    mock_agents = {"Researcher": AsyncMock(), "Analyst": AsyncMock()}
    mock_agents["Researcher"].run.return_value = "Research Results"
    mock_agents["Analyst"].run.return_value = "Analysis Results"

    # Initialize Workflow
    mock_history_manager = MagicMock()
    workflow = SupervisorWorkflow(
        dspy_supervisor=mock_supervisor, agents=mock_agents, history_manager=mock_history_manager
    )
    # Run Workflow
    # Note: We are testing the legacy/adapter path here which mimics the fleet behavior
    # because setting up the full Agent Framework graph in a unit test is complex
    # and requires the actual Agent Framework runtime.
    # The adapter logic _is_ the synergy logic we want to test (it orchestrates the calls).
    result = await workflow.run("Test Task")

    # Verification
    assert result["result"] == "Analysis Results"  # Last agent's output
    assert result["quality"]["score"] == 9.0

    # Verify Synergy Calls
    mock_supervisor.analyze_task.assert_called_once()
    mock_supervisor.route_task.assert_called_once()
    # decide_tools is called inside the execution loop (if enabled),
    # but in the legacy adapter path it might be skipped or handled differently.
    # Let's verify the routing decision was respected.
    assert mock_agents["Researcher"].run.called
    assert mock_agents["Analyst"].run.called


@pytest.mark.asyncio
async def test_workflow_synergy_refinement_loop():
    """Test the Quality -> Refinement loop synergy."""

    mock_supervisor = MagicMock(spec=DSPySupervisor)

    # Setup for Refinement
    # 1. Initial Analysis/Routing
    mock_supervisor.analyze_task.return_value = {"complexity": "low"}
    mock_supervisor.route_task.return_value = {
        "task": "Write Code",
        "assigned_to": ["Writer"],
        "mode": ExecutionMode.DELEGATED.value,
        "subtasks": [],
    }

    # 2. Initial Quality (Low Score)
    mock_supervisor.assess_quality.return_value = {
        "score": 5.0,
        "missing": "No comments",
        "improvements": "Add comments",
    }

    # 3. Progress Evaluation (Refine)
    mock_supervisor.evaluate_progress.return_value = {
        "action": "refine",
        "feedback": "Add comments",
    }

    mock_agents = {"Writer": AsyncMock()}
    # First run: Code without comments
    # Second run (Refinement): Code with comments
    mock_agents["Writer"].run.side_effect = ["def foo(): pass", "def foo(): # comment\n pass"]

    # Config with refinement enabled
    from agentic_fleet.workflows.config import WorkflowConfig

    config = WorkflowConfig(enable_refinement=True, refinement_threshold=8.0)

    workflow = SupervisorWorkflow(
        dspy_supervisor=mock_supervisor,
        agents=mock_agents,
        context=config,  # Pass config as context for legacy adapter
    )

    result = await workflow.run("Write Code")

    # Verification
    assert result["result"] == "def foo(): # comment\n pass"
    assert mock_agents["Writer"].run.call_count == 2  # Initial + Refinement
    mock_supervisor.evaluate_progress.assert_called()
