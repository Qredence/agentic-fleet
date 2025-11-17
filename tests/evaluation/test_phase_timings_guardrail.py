from __future__ import annotations

from types import SimpleNamespace

import pytest

from agentic_fleet.workflows.shared.analysis import run_analysis_phase
from agentic_fleet.workflows.shared.progress import run_progress_phase
from agentic_fleet.workflows.shared.routing import run_routing_phase


class DummySupervisor:
    async def analyze_task(self, task: str, perform_search: bool = False):
        return {
            "complexity": "simple",
            "required_capabilities": "general_reasoning",
            "tool_requirements": "",
            "estimated_steps": "3",
            "search_context": "",
            "needs_web_search": "no",
            "search_query": "",
        }

    async def evaluate_progress(self, original_task: str, completed: str, current_status: str):
        return {"next_action": "complete", "feedback": ""}

    async def perform_web_search_async(self, query: str):
        return "n/a"

    async def route_task(self, task: str, team: dict[str, str], context: str = ""):
        return {
            "assigned_to": "Researcher",
            "execution_mode": "delegated",
            "subtasks": task,
            "confidence": "0.9",
        }


def _normalize_analysis(payload: dict, _task: str) -> dict:
    return payload


def _fallback_analysis(_task: str) -> dict:
    return {
        "complexity": "simple",
        "required_capabilities": "general_reasoning",
        "tool_requirements": "",
        "estimated_steps": "3",
        "search_context": "",
        "needs_web_search": "no",
        "search_query": "",
    }


def _validate_routing_prediction(payload: dict, _task: str):
    return SimpleNamespace(
        task=_task,
        assigned_to=("Researcher",),
        mode=SimpleNamespace(value="delegated"),
        subtasks=(_task,),
        tool_requirements=tuple(),
        confidence=0.9,
    )


def _normalize_routing_decision(routing, _task: str):
    return routing


def _fallback_routing(_task: str):
    return _validate_routing_prediction({}, _task)


def _normalize_progress(payload: dict) -> dict:
    return {"action": "complete", "feedback": "", "used_fallback": False}


def _fallback_progress() -> dict:
    return {"action": "continue", "feedback": "", "used_fallback": True}


async def _call_with_retry(fn, *args, **kwargs):
    res = fn(*args, **kwargs)
    if hasattr(res, "__await__"):
        return await res
    return res


def _record_phase_status(container: dict[str, str]):
    def _rec(phase: str, status: str) -> None:
        container[phase] = status

    return _rec


@pytest.mark.asyncio
async def test_phase_timings_and_statuses():
    # Minimal context
    config = SimpleNamespace(slow_execution_threshold=999999)  # effectively disabled
    context = SimpleNamespace(
        config=config,
        analysis_cache=None,
        agents={"Researcher": SimpleNamespace(description="Research & search")},
        latest_phase_timings={},
        latest_phase_status={},
    )

    supervisor = DummySupervisor()

    # Analysis
    analysis = await run_analysis_phase(
        task="Quick test task",
        context=context,
        compiled_supervisor=supervisor,
        supervisor=supervisor,
        call_with_retry=_call_with_retry,
        normalize_analysis_result=_normalize_analysis,
        fallback_analysis=_fallback_analysis,
        record_phase_status=_record_phase_status(context.latest_phase_status),
    )
    assert analysis.complexity in {"simple", "moderate", "complex"}
    assert "analysis" in context.latest_phase_timings
    assert context.latest_phase_timings["analysis"] >= 0.0
    assert context.latest_phase_status.get("analysis") in {"success", "fallback", "cached"}

    # Routing
    plan = await run_routing_phase(
        task="Quick test task",
        analysis=analysis,
        context=context,
        call_with_retry=_call_with_retry,
        compiled_supervisor=supervisor,
        validate_routing_prediction=_validate_routing_prediction,
        normalize_routing_decision_fn=_normalize_routing_decision,
        fallback_routing_decision=_fallback_routing,
        record_phase_status=_record_phase_status(context.latest_phase_status),
    )
    assert plan.decision.assigned_to
    assert "routing" in context.latest_phase_timings
    assert context.latest_phase_timings["routing"] >= 0.0
    assert context.latest_phase_status.get("routing") in {"success", "fallback"}

    # Progress
    progress = await run_progress_phase(
        task="Quick test task",
        result="ok",
        context=context,
        supervisor=supervisor,
        call_with_retry=_call_with_retry,
        normalize_progress=_normalize_progress,
        fallback_progress=_fallback_progress,
        record_phase_status=_record_phase_status(context.latest_phase_status),
    )
    assert progress.action in {"continue", "complete", "refine", "escalate"}
    assert "progress" in context.latest_phase_timings
    assert context.latest_phase_timings["progress"] >= 0.0
    assert context.latest_phase_status.get("progress") in {"success", "fallback"}
