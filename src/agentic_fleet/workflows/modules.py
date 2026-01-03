"""Workflow graph modules for dynamic routing."""

from typing import Any

from agent_framework import (
    AgentExecutorResponse,
    Case,
    Default,
    Executor,
    Workflow,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)

from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.agents.router import RouterAgent
from agentic_fleet.dspy_modules.signatures import JudgeSignature, PlannerSignature, WorkerSignature


ROUTE_PATTERN_NORMALIZATION = {
    "direct_answer": "direct",
    "simple_tool": "simple",
    "complex_council": "complex",
}


def _normalize_route_pattern(value: str) -> str:
    lowered = value.lower()
    return ROUTE_PATTERN_NORMALIZATION.get(lowered, lowered)


def _extract_route_pattern(message: Any) -> str:
    if isinstance(message, AgentExecutorResponse):
        meta = message.agent_run_response.additional_properties or {}
        pattern = meta.get("route_pattern")
        if pattern:
            return _normalize_route_pattern(str(pattern))
        if message.full_conversation:
            for msg in message.full_conversation:
                if getattr(msg, "additional_properties", None):
                    pattern = msg.additional_properties.get("route_pattern")
                    if pattern:
                        return _normalize_route_pattern(str(pattern))
        if message.full_conversation:
            for msg in message.full_conversation:
                text = getattr(msg, "text", "") or ""
                if "routing to" in text.lower():
                    extracted = text.lower().split("routing to", 1)[-1].strip()
                    return _normalize_route_pattern(extracted)
    return ""


def _is_complex(message: Any) -> bool:
    return _extract_route_pattern(message) == "complex"


def _is_simple(message: Any) -> bool:
    return _extract_route_pattern(message) == "simple"


def _is_direct(message: Any) -> bool:
    return _extract_route_pattern(message) == "direct"


class TerminalExecutor(Executor):
    """Terminal sink that ends execution without emitting further messages."""

    @handler
    async def finalize(self, _: AgentExecutorResponse, ctx: WorkflowContext[None]) -> None:
        return None


def build_modules_workflow(planner_state_path: str | None = None) -> Workflow:
    builder = WorkflowBuilder(name="modules-workflow", description="Router -> Planner -> Worker -> Judge")

    builder.register_executor(lambda: TerminalExecutor(id="Terminal"), name="Terminal")
    builder.register_agent(lambda: RouterAgent(), name="Router")
    builder.register_agent(
        lambda: BaseFleetAgent(
            "Planner",
            "architect",
            PlannerSignature,
            brain_state_path=planner_state_path,
            model_role="planner",
        ),
        name="Planner",
    )
    builder.register_agent(
        lambda: BaseFleetAgent("Worker", "executor", WorkerSignature, model_role="worker"),
        name="Worker",
        output_response=True,
    )
    builder.register_agent(
        lambda: BaseFleetAgent("Judge", "critic", JudgeSignature, model_role="judge"),
        name="Judge",
        output_response=True,
    )

    builder.set_start_executor("Router")

    builder.add_switch_case_edge_group(
        "Router",
        [
            Case(condition=_is_complex, target="Planner"),
            Default(target="Worker"),
        ],
    )

    builder.add_edge("Planner", "Worker")
    builder.add_switch_case_edge_group(
        "Worker",
        [
            Case(condition=_is_complex, target="Judge"),
            Default(target="Terminal"),
        ],
    )
    builder.add_edge("Judge", "Terminal")

    return builder.build()
