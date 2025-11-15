"""Enhanced tests for supervisor workflow."""

from __future__ import annotations

import asyncio
from typing import Any

import dspy
import pytest

from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow, WorkflowConfig


class DummyAgent:
    def __init__(self, name: str, description: str = "stub agent", should_fail: bool = False):
        self.name = name
        self.description = description
        self.calls: list[str] = []
        self.should_fail = should_fail

    async def run(self, task: str) -> str:
        self.calls.append(task)
        await asyncio.sleep(0)
        if self.should_fail:
            raise RuntimeError(f"{self.name} intentionally failed")
        return f"{self.name}:{task}"


class StubDSPySupervisor(dspy.Module):
    def __init__(self, routing: dict[str, Any]):
        self._routing = routing

    def analyze_task(self, task: str) -> dict[str, Any]:
        return {"complexity": "simple", "capabilities": ["analysis"], "steps": 1}

    def route_task(self, task: str, team: dict[str, str], context: str = "") -> dict[str, Any]:
        result = {"task": task}
        result.update(self._routing)
        return result

    def evaluate_progress(self, **_: Any) -> dict[str, Any]:
        return {"action": "complete", "feedback": ""}

    def assess_quality(self, **_: Any) -> dict[str, Any]:
        return {"score": 10, "missing": "", "improvements": ""}

    def get_execution_summary(self) -> dict[str, Any]:
        return {"total_routings": 1, "routing_history": [], "execution_context": []}


@pytest.mark.asyncio
async def test_run_falls_back_to_available_agent():
    """Test that unknown agents fall back to available ones."""
    workflow = SupervisorWorkflow()
    workflow.agents = {"Writer": DummyAgent("Writer")}
    workflow.dspy_supervisor = StubDSPySupervisor(  # type: ignore[assignment]
        routing={"assigned_to": ["Ghost"], "mode": "parallel", "subtasks": []}
    )

    result = await workflow.run("demo task")

    assert result["routing"]["assigned_to"] == ["Writer"]
    assert result["result"] == "Writer:demo task"
    assert workflow.agents["Writer"].calls == ["demo task"]


@pytest.mark.asyncio
async def test_run_stream_normalizes_parallel_subtasks(monkeypatch):
    """Test that parallel subtasks are normalized correctly."""
    workflow = SupervisorWorkflow()
    workflow.agents = {
        "Researcher": DummyAgent("Researcher"),
        "Analyst": DummyAgent("Analyst"),
    }
    workflow.dspy_supervisor = StubDSPySupervisor(  # type: ignore[assignment]
        routing={
            "assigned_to": ["Researcher", "Analyst"],
            "mode": "parallel",
            "subtasks": ["collect context"],
        }
    )
    workflow.history_manager.save_execution = lambda execution: "logs/test.jsonl"

    events = []
    async for event in workflow.run_stream("complex task"):
        events.append(event)

    final_event = events[-1]
    assert hasattr(final_event, "data")
    assert "result" in final_event.data
    assert "Researcher:collect context" in final_event.data["result"]
    assert "Analyst:complex task" in final_event.data["result"]
    assert workflow.current_execution["routing"]["subtasks"] == [
        "collect context",
        "complex task",
    ]


@pytest.mark.asyncio
async def test_parallel_execution_handles_failures():
    """Test that parallel execution handles individual agent failures gracefully."""
    workflow = SupervisorWorkflow()
    workflow.agents = {
        "GoodAgent": DummyAgent("GoodAgent", should_fail=False),
        "BadAgent": DummyAgent("BadAgent", should_fail=True),
    }

    result = await workflow._execute_parallel(["GoodAgent", "BadAgent"], ["task1", "task2"])

    assert "GoodAgent:task1" in result
    assert "BadAgent failed" in result


@pytest.mark.asyncio
async def test_single_agent_parallel_mode_converts_to_delegated():
    """Test that parallel mode with single agent converts to delegated."""
    workflow = SupervisorWorkflow()
    workflow.agents = {"Writer": DummyAgent("Writer")}
    workflow.dspy_supervisor = StubDSPySupervisor(  # type: ignore[assignment]
        routing={"assigned_to": ["Writer"], "mode": "parallel", "subtasks": []}
    )

    result = await workflow.run("demo task")

    assert result["routing"]["mode"] == "delegated"
    assert result["routing"]["assigned_to"] == ["Writer"]


@pytest.mark.asyncio
async def test_refinement_threshold_configurable():
    """Test that refinement threshold is configurable."""
    config = WorkflowConfig(refinement_threshold=9.0, enable_refinement=True, compile_dspy=False)
    workflow = SupervisorWorkflow(config)
    workflow.agents = {"Writer": DummyAgent("Writer")}
    workflow.dspy_supervisor = StubDSPySupervisor(  # type: ignore[assignment]
        routing={"assigned_to": ["Writer"], "mode": "delegated", "subtasks": []}
    )

    # Mock quality assessment to return score below threshold
    def mock_assess_quality(**_):
        return {"score": 8.5, "missing": "", "improvements": "minor tweaks"}

    workflow.dspy_supervisor.assess_quality = mock_assess_quality  # type: ignore[method-assign]

    # Mock progress evaluation to suggest refinement
    def mock_evaluate_progress(**_):
        return {"action": "refine", "feedback": "needs improvement"}

    workflow.dspy_supervisor.evaluate_progress = mock_evaluate_progress  # type: ignore[method-assign]

    await workflow.run("demo task")

    # Score is below threshold (9.0), so refinement should occur
    assert workflow.agents["Writer"].calls[-1].startswith("Refine these results")


@pytest.mark.asyncio
async def test_completion_storage_disabled_by_default():
    """Test that completion storage is disabled by default."""
    config = WorkflowConfig()
    assert config.enable_completion_storage is False


@pytest.mark.asyncio
async def test_graceful_tavily_missing(monkeypatch):
    """Test graceful handling when TAVILY_API_KEY is missing."""
    # Clear TAVILY_API_KEY
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    workflow = SupervisorWorkflow(WorkflowConfig(compile_dspy=False))

    # Call _create_agents directly
    workflow.agents = workflow._create_agents()

    # Should not raise, Researcher should be created without tool
    assert "Researcher" in workflow.agents

    # Verify that no TavilySearchTool was registered in the tool registry
    researcher_tools = workflow.tool_registry.get_agent_tools("Researcher")
    assert len(researcher_tools) == 0, "Researcher should have no tools when Tavily is missing"
