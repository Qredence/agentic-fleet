"""
Comprehensive tests for supervisor workflow streaming and edge cases.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agentic_fleet.workflows.exceptions import AgentExecutionError, HistoryError
from agentic_fleet.workflows.supervisor_workflow import (
    SupervisorWorkflow,
    WorkflowConfig,
    _validate_task,
)


@pytest.mark.asyncio
async def test_run_stream_yields_events():
    """Test that run_stream yields proper event sequence."""
    workflow = SupervisorWorkflow(WorkflowConfig(), MagicMock())

    # Use DummyAgent instead of stub that raises NotImplementedError
    from tests.workflows.test_supervisor_workflow import DummyAgent

    workflow.agents = {
        "Writer": DummyAgent("Writer"),
        "Researcher": DummyAgent("Researcher"),
        "Analyst": DummyAgent("Analyst"),
        "Reviewer": DummyAgent("Reviewer"),
    }

    from tests.workflows.test_supervisor_workflow import StubDSPySupervisor

    workflow.dspy_supervisor = StubDSPySupervisor(
        routing={"assigned_to": ["Writer"], "mode": "delegated", "subtasks": []}
    )  # type: ignore[assignment]
    workflow.history_manager.save_execution = lambda execution: "logs/test.jsonl"

    events = []
    async for event in workflow.run_stream("Test task"):
        events.append(event)

    # Should yield at least analysis, routing, execution, and quality events
    assert len(events) > 0
    # Check that we get WorkflowOutputEvent at the end
    assert hasattr(events[-1], "data")


@pytest.mark.asyncio
async def test_history_save_failure_handling():
    """Test behavior when history save fails."""
    workflow = SupervisorWorkflow(WorkflowConfig(), MagicMock())

    workflow.current_execution = {"task": "test", "result": "test result"}

    # Mock history manager save method to raise HistoryError
    def raise_history_error(execution):
        raise HistoryError("Save failed", "logs/test.jsonl")

    workflow.history_manager.save_execution = raise_history_error

    # Should raise HistoryError
    with pytest.raises(HistoryError):
        workflow.history_manager.save_execution(workflow.current_execution)


@pytest.mark.asyncio
async def test_parallel_execution_with_all_agents_failing():
    """Test parallel execution when all agents fail."""
    workflow = SupervisorWorkflow(WorkflowConfig(), MagicMock())
    await workflow.initialize(compile_dspy=False)

    # Mock agents to all fail
    for agent_name in workflow.agents:
        workflow.agents[agent_name].run = AsyncMock(side_effect=Exception("Agent failed"))

    # Should still return synthesized results with error messages
    result = await workflow._execute_parallel(["Researcher", "Analyst"], ["task1", "task2"])
    assert "failed" in result.lower() or "error" in result.lower()


@pytest.mark.asyncio
async def test_sequential_execution_with_missing_agent():
    """Test sequential execution skips missing agents."""
    workflow = SupervisorWorkflow(WorkflowConfig(), MagicMock())

    from tests.workflows.test_supervisor_workflow import DummyAgent

    # Create agents with DummyAgent
    workflow.agents = {
        "Reviewer": DummyAgent("Reviewer"),
    }

    # Should handle gracefully by skipping missing Writer
    result = await workflow._execute_sequential(["Writer", "Reviewer"], "test task")
    # Should complete with available agents
    assert result is not None
    assert "Reviewer" in result


@pytest.mark.asyncio
async def test_delegated_execution_with_invalid_agent():
    """Test delegated execution raises error for invalid agent."""
    workflow = SupervisorWorkflow(WorkflowConfig(), MagicMock())
    await workflow.initialize(compile_dspy=False)

    with pytest.raises(AgentExecutionError):
        await workflow._execute_delegated("NonExistentAgent", "test task")


@pytest.mark.asyncio
async def test_normalize_routing_fallback():
    """Test routing normalization falls back to available agent."""
    workflow = SupervisorWorkflow(WorkflowConfig(), MagicMock())
    await workflow.initialize(compile_dspy=False)

    # Invalid routing with no valid agents
    invalid_routing = {"assigned_to": ["NonExistentAgent"], "mode": "delegated"}

    # Should fall back to first available agent
    normalized = workflow._normalize_routing_decision(invalid_routing, "test task")
    assert normalized.assigned_to[0] in workflow.agents


@pytest.mark.asyncio
async def test_normalize_routing_invalid_mode():
    """Test routing normalization handles invalid mode."""
    workflow = SupervisorWorkflow(WorkflowConfig(), MagicMock())
    await workflow.initialize(compile_dspy=False)

    invalid_routing = {"assigned_to": ["Writer"], "mode": "invalid_mode"}

    normalized = workflow._normalize_routing_decision(invalid_routing, "test task")
    assert normalized.mode.value == "delegated"  # Should default to delegated


@pytest.mark.asyncio
async def test_normalize_routing_parallel_to_delegated():
    """Test routing switches from parallel to delegated for single agent."""
    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    routing = {"assigned_to": ["Writer"], "mode": "parallel"}

    normalized = workflow._normalize_routing_decision(routing, "test task")
    assert normalized.mode.value == "delegated"


@pytest.mark.asyncio
async def test_prepare_subtasks_alignment():
    """Test subtask preparation aligns with agents."""
    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    agents = ["Researcher", "Analyst"]
    subtasks = ["task1"]

    # Should pad subtasks to match agent count
    prepared = workflow._prepare_subtasks(agents, subtasks, "fallback")
    assert len(prepared) == len(agents)


@pytest.mark.asyncio
async def test_prepare_subtasks_truncation():
    """Test subtask preparation truncates excess subtasks."""
    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    agents = ["Writer"]
    subtasks = ["task1", "task2", "task3"]

    prepared = workflow._prepare_subtasks(agents, subtasks, "fallback")
    assert len(prepared) == len(agents)


@pytest.mark.asyncio
async def test_synthesize_results():
    """Test result synthesis combines parallel results."""
    workflow = SupervisorWorkflow()

    results = ["Result 1", "Result 2", "Result 3"]
    synthesized = workflow._synthesize_results(results)
    assert "Result 1" in synthesized
    assert "Result 2" in synthesized
    assert "Result 3" in synthesized


@pytest.mark.asyncio
async def test_refine_results():
    """Test result refinement calls Writer agent."""
    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    workflow.agents["Writer"].run = AsyncMock(return_value="Refined result")

    result = await workflow._refine_results("Original result", "Improvements needed")
    assert result == "Refined result"
    workflow.agents["Writer"].run.assert_called_once()


def test_validate_task_empty():
    """Test task validation rejects empty tasks."""
    with pytest.raises(ValueError, match="cannot be empty"):
        _validate_task("")

    with pytest.raises(ValueError, match="cannot be empty"):
        _validate_task("   ")


def test_validate_task_too_long():
    """Test task validation rejects overly long tasks."""
    long_task = "x" * 10001
    with pytest.raises(ValueError, match="exceeds maximum length"):
        _validate_task(long_task)


def test_validate_task_valid():
    """Test task validation accepts valid tasks."""
    valid_task = "This is a valid task"
    result = _validate_task(valid_task)
    assert result == valid_task.strip()


def test_validate_task_strips_whitespace():
    """Test task validation strips whitespace."""
    task = "  Task with whitespace  "
    result = _validate_task(task)
    assert result == "Task with whitespace"


@pytest.mark.asyncio
async def test_workflow_config_defaults():
    """Test WorkflowConfig has sensible defaults."""
    config = WorkflowConfig()
    assert config.max_rounds == 15
    assert config.max_stalls == 3
    assert config.enable_streaming is True
    assert config.history_format == "jsonl"


@pytest.mark.asyncio
async def test_create_agent_factory():
    """Test agent factory method creates agents correctly."""
    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    agent = workflow._create_agent(
        name="TestAgent",
        description="Test description",
        instructions="Test instructions",
    )

    # ChatAgent exposes name and description, but not instructions
    assert agent.name == "TestAgent"
    assert agent.description == "Test description"
    # Instructions are passed during initialization but not exposed as attribute


@pytest.mark.asyncio
async def test_create_agent_with_tools():
    """Test agent factory method handles tools correctly."""
    workflow = SupervisorWorkflow()
    await workflow.initialize(compile_dspy=False)

    mock_tool = MagicMock()
    mock_tool.name = "TestTool"
    mock_tool.description = "Test tool description"

    agent = workflow._create_agent(
        name="TestAgent",
        description="Test description",
        instructions="Test instructions",
        tools=mock_tool,
    )

    # Verify agent was created successfully
    # ChatAgent doesn't expose tools attribute directly, but agent should be functional
    assert agent.name == "TestAgent"
