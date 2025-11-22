"""Tests for execution strategies (delegated, sequential, parallel)."""

import pytest

from agentic_fleet.workflows.exceptions import AgentExecutionError
from agentic_fleet.workflows.strategies import (
    delegated,
    execute_delegated,
    execute_delegated_streaming,
    execute_parallel,
    execute_parallel_streaming,
    execute_sequential,
    execute_sequential_streaming,
    format_handoff_input,
    parallel,
    sequential,
)


@pytest.mark.asyncio
async def test_execute_delegated_with_single_agent():
    """Test delegated execution with single agent."""
    agent_name = "Researcher"
    task = "Research topic X"

    class MockAgent:
        async def run(self, prompt: str):
            return f"Result: {prompt}"

    agents = {agent_name: MockAgent()}
    result = await execute_delegated(agents, agent_name, task)

    assert result == f"Result: {task}"


@pytest.mark.asyncio
async def test_execute_delegated_missing_agent():
    """Test delegated execution raises error when agent not found."""
    agents = {}
    agent_name = "Researcher"
    task = "Research topic X"

    with pytest.raises(AgentExecutionError) as exc_info:
        await execute_delegated(agents, agent_name, task)

    assert agent_name in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_delegated_streaming():
    """Test delegated execution with streaming."""
    agent_name = "Researcher"
    task = "Research topic X"

    class MockAgent:
        async def run(self, prompt: str):
            return f"Result: {prompt}"

    agents = {agent_name: MockAgent()}

    events = []
    async for event in execute_delegated_streaming(agents, agent_name, task):
        events.append(event)

    assert len(events) >= 2  # Should have at least start and completion events
    assert any(isinstance(e, delegated.MagenticAgentMessageEvent) for e in events)
    assert any(isinstance(e, delegated.WorkflowOutputEvent) for e in events)


@pytest.mark.asyncio
async def test_execute_delegated_streaming_with_progress_callback():
    """Test delegated execution with streaming and progress callback."""
    agent_name = "Researcher"
    task = "Research topic X"

    class MockAgent:
        async def run(self, prompt: str):
            return f"Result: {prompt}"

    progress_calls = []

    class MockProgressCallback:
        def on_progress(self, message: str, current: int = 0, total: int = 0):
            progress_calls.append(message)

    agents = {agent_name: MockAgent()}
    progress_callback = MockProgressCallback()

    events = []
    async for event in execute_delegated_streaming(agents, agent_name, task, progress_callback):
        events.append(event)

    assert len(progress_calls) > 0
    assert any("Executing" in call for call in progress_calls)


@pytest.mark.asyncio
async def test_execute_parallel_with_multiple_agents():
    """Test parallel execution with multiple agents."""
    agent_names = ["Researcher", "Analyst"]
    subtasks = ["Research topic A", "Analyze topic B"]

    class MockAgent:
        def __init__(self, name):
            self.name = name

        async def run(self, prompt: str):
            return f"{self.name}: {prompt}"

    agents = {name: MockAgent(name) for name in agent_names}
    result, _ = await execute_parallel(agents, agent_names, subtasks)

    assert "Researcher" in result
    assert "Analyst" in result


@pytest.mark.asyncio
async def test_execute_parallel_with_missing_agent():
    """Test parallel execution skips missing agents."""
    agent_names = ["Researcher", "MissingAgent"]
    subtasks = ["Research topic A", "Task B"]

    class MockAgent:
        def __init__(self, name):
            self.name = name

        async def run(self, prompt: str):
            return f"{self.name}: {prompt}"

    agents = {"Researcher": MockAgent("Researcher")}
    result, _ = await execute_parallel(agents, agent_names, subtasks)

    # Should only have Researcher result
    assert "Researcher" in result
    assert "MissingAgent" not in result


@pytest.mark.asyncio
async def test_execute_parallel_no_valid_agents():
    """Test parallel execution raises error when no valid agents."""
    agent_names = ["MissingAgent1", "MissingAgent2"]
    subtasks = ["Task A", "Task B"]
    agents = {}

    with pytest.raises(AgentExecutionError) as exc_info:
        await execute_parallel(agents, agent_names, subtasks)

    # Check that the original error message contains "No valid agents"
    assert "No valid agents" in str(exc_info.value.original_error)


@pytest.mark.asyncio
async def test_execute_parallel_with_exceptions():
    """Test parallel execution handles exceptions gracefully."""
    agent_names = ["Researcher", "FailingAgent"]
    subtasks = ["Research topic A", "Task B"]

    class MockAgent:
        def __init__(self, name, should_fail=False):
            self.name = name
            self.should_fail = should_fail

        async def run(self, prompt: str):
            if self.should_fail:
                raise RuntimeError("Agent failed")
            return f"{self.name}: {prompt}"

    agents = {
        "Researcher": MockAgent("Researcher", should_fail=False),
        "FailingAgent": MockAgent("FailingAgent", should_fail=True),
    }
    result, _ = await execute_parallel(agents, agent_names, subtasks)

    # Should include failure message for failing agent
    assert "Researcher" in result
    assert "failed" in result.lower()


@pytest.mark.asyncio
async def test_execute_parallel_streaming():
    """Test parallel execution with streaming."""
    agent_names = ["Researcher", "Analyst"]
    subtasks = ["Research topic A", "Analyze topic B"]

    class MockAgent:
        def __init__(self, name):
            self.name = name

        async def run(self, prompt: str):
            return f"{self.name}: {prompt}"

    agents = {name: MockAgent(name) for name in agent_names}

    events = []
    async for event in execute_parallel_streaming(agents, agent_names, subtasks):
        events.append(event)

    # Should have start events, completion events, and final output
    assert len(events) >= len(agent_names) + 1  # At least one per agent + final output
    assert any(isinstance(e, parallel.WorkflowOutputEvent) for e in events)


@pytest.mark.asyncio
async def test_execute_parallel_streaming_with_progress():
    """Test parallel execution with streaming and progress callback."""
    agent_names = ["Researcher", "Analyst"]
    subtasks = ["Research topic A", "Analyze topic B"]

    class MockAgent:
        def __init__(self, name):
            self.name = name

        async def run(self, prompt: str):
            return f"{self.name}: {prompt}"

    progress_calls = []

    class MockProgressCallback:
        def on_progress(self, message: str, current: int = 0, total: int = 0):
            progress_calls.append((message, current, total))

    agents = {name: MockAgent(name) for name in agent_names}
    progress_callback = MockProgressCallback()

    events = []
    async for event in execute_parallel_streaming(agents, agent_names, subtasks, progress_callback):
        events.append(event)

    assert len(progress_calls) > 0
    # Should have progress updates
    assert any("parallel" in call[0].lower() for call in progress_calls)


@pytest.mark.asyncio
async def test_execute_sequential_standard_flow():
    """Test sequential execution standard flow."""
    agent_names = ["Researcher", "Writer"]
    task = "Research and write about X"

    class MockAgent:
        def __init__(self, name):
            self.name = name

        async def run(self, prompt: str):
            return f"{self.name} processed: {prompt}"

    agents = {name: MockAgent(name) for name in agent_names}
    result, _ = await execute_sequential(agents, agent_names, task)

    # Result should be processed by both agents
    assert "Writer" in result
    assert "processed" in result


@pytest.mark.asyncio
async def test_execute_sequential_with_missing_agent():
    """Test sequential execution skips missing agents."""
    agent_names = ["Researcher", "MissingAgent", "Writer"]
    task = "Research and write about X"

    class MockAgent:
        def __init__(self, name):
            self.name = name

        async def run(self, prompt: str):
            return f"{self.name} processed: {prompt}"

    agents = {
        "Researcher": MockAgent("Researcher"),
        "Writer": MockAgent("Writer"),
    }
    result, _ = await execute_sequential(agents, agent_names, task)

    # Should still work, skipping MissingAgent
    assert "Writer" in result


@pytest.mark.asyncio
async def test_execute_sequential_empty_agent_list():
    """Test sequential execution raises error with empty agent list."""
    agents = {}
    agent_names = []
    task = "Some task"

    with pytest.raises(AgentExecutionError) as exc_info:
        await execute_sequential(agents, agent_names, task)

    # Check that the original error message contains "at least one agent"
    assert "at least one agent" in str(exc_info.value.original_error).lower()


@pytest.mark.asyncio
async def test_execute_sequential_with_handoffs():
    """Test sequential execution with handoffs enabled."""
    from agentic_fleet.dspy_modules.reasoner import DSPyReasoner
    from agentic_fleet.workflows.handoff import HandoffManager

    agent_names = ["Researcher", "Analyst"]
    task = "Research and analyze X"

    class MockAgent:
        def __init__(self, name):
            self.name = name
            self.description = f"{name} description"

        async def run(self, prompt: str):
            return f"{self.name} result: {prompt}"

    agents = {name: MockAgent(name) for name in agent_names}

    supervisor = DSPyReasoner()
    handoff_manager = HandoffManager(supervisor)

    result, _ = await execute_sequential(
        agents, agent_names, task, enable_handoffs=True, handoff=handoff_manager
    )

    # Should execute with handoffs
    assert len(result) > 0
    # Handoff history should be populated if handoffs occurred
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_execute_sequential_streaming():
    """Test sequential execution with streaming."""
    agent_names = ["Researcher", "Writer"]
    task = "Research and write about X"

    class MockAgent:
        def __init__(self, name):
            self.name = name

        async def run(self, prompt: str):
            return f"{self.name} processed: {prompt}"

    agents = {name: MockAgent(name) for name in agent_names}

    events = []
    async for event in execute_sequential_streaming(agents, agent_names, task):
        events.append(event)

    # Should have events for each agent and final output
    assert len(events) >= len(agent_names) + 1
    assert any(isinstance(e, sequential.WorkflowOutputEvent) for e in events)


@pytest.mark.asyncio
async def test_format_handoff_input():
    """Test formatting handoff input."""
    from agentic_fleet.workflows.handoff import HandoffContext

    handoff = HandoffContext(
        from_agent="Researcher",
        to_agent="Analyst",
        task="Analyze data",
        work_completed="Gathered 100 data points",
        artifacts={"data.csv": "sample data"},
        remaining_objectives=["Analyze trends", "Create visualizations"],
        success_criteria=["Analysis complete", "Charts created"],
        tool_requirements=["HostedCodeInterpreterTool"],
        estimated_effort="moderate",
        quality_checklist=["Verify data quality", "Check calculations"],
    )

    formatted = format_handoff_input(handoff)

    assert "HANDOFF FROM Researcher" in formatted
    assert "Work Completed" in formatted
    assert "Your Objectives" in formatted
    assert "Analyze trends" in formatted
    assert "Success Criteria" in formatted
    assert "Quality Checklist" in formatted
    assert "Required Tools" in formatted
