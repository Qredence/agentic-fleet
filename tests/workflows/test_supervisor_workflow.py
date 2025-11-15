from __future__ import annotations

import asyncio
from typing import Any

import dspy
import pytest

from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow


class DummyAgent:
    def __init__(self, name: str, description: str = "stub agent"):
        self.name = name
        self.description = description
        self.calls: list[str] = []

    async def run(self, task: str) -> str:
        self.calls.append(task)
        await asyncio.sleep(0)  # ensure proper scheduling
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
        return {"total_routings": 1}


@pytest.mark.asyncio
async def test_run_falls_back_to_available_agent():
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
    # Avoid writing execution history files during tests
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
