"""Utilities for building experimental dynamic workflows.

This module provides a very small abstraction on top of ``agent_framework``
to make it easy for tests (and curious developers) to spin up a toy workflow
composed of the four backbone participants that historically powered the
"dynamic" workflow prototype: ``planner``, ``executor``, ``verifier`` and
``generator``.  The production codebase no longer depends on this module, but
older tests and tutorials still import it.  Recent refactors accidentally
removed the file which resulted in import errors during test collection.

The helpers below intentionally keep the behaviour minimal – the goal is to
offer type-safe factories that return working ``agent_framework`` executors so
that ``WorkflowBuilder`` can stitch them together.  This keeps the public
surface area compatible with what the tests expect without reviving the full
feature set of the original prototype.
"""

import json
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

from agent_framework import Executor, Workflow, WorkflowBuilder, WorkflowContext, handler

ExecutorFactory = Callable[[], Executor]


@dataclass
class DynamicWorkflowParticipants:
    """Container describing the factories used to construct the workflow."""

    backbone: dict[str, ExecutorFactory]
    tools: dict[str, ExecutorFactory]

    def __init__(
        self,
        backbone: Mapping[str, ExecutorFactory],
        tools: Mapping[str, ExecutorFactory] | None = None,
    ) -> None:
        self.backbone = dict(backbone)
        self.tools = dict(tools or {})

    def as_dict(self) -> dict[str, dict[str, ExecutorFactory]]:
        """Return a serialisable view of the participants."""

        return {"backbone": dict(self.backbone), "tools": dict(self.tools)}

    def with_tool_agents(
        self, tools: Mapping[str, ExecutorFactory]
    ) -> "DynamicWorkflowParticipants":
        """Return a copy with additional tool agents."""

        merged = dict(self.tools)
        merged.update(tools)
        return DynamicWorkflowParticipants(self.backbone, merged)


@dataclass
class ExecutionResult:
    """Result emitted by the executor for verification."""

    prompt: str
    content: str
    approved: bool = False
    feedback: str | None = None


class Planner(Executor):
    """Simple planner that wraps the incoming prompt."""

    def __init__(self) -> None:
        super().__init__(id="planner")

    @handler
    async def plan(self, message: str, ctx: WorkflowContext[str, str]) -> None:
        await ctx.send_message(message)


class WorkerExecutor(Executor):
    """Executor that generates a draft response for the verifier."""

    def __init__(self) -> None:
        super().__init__(id="executor")

    @handler
    async def handle(self, request: str, ctx: WorkflowContext[str, str]) -> None:
        import dataclasses

        result = ExecutionResult(prompt=request, content=f"Draft response: {request}")
        await ctx.send_message(json.dumps(dataclasses.asdict(result)))


class Verifier(Executor):
    """Verifier that rubber-stamps the worker output."""

    def __init__(self) -> None:
        super().__init__(id="verifier")

    @handler
    async def review(self, message: str, ctx: WorkflowContext[str, str]) -> None:
        data = json.loads(message)
        result = ExecutionResult(**data)
        approved_result = ExecutionResult(
            prompt=result.prompt, content=result.content, approved=True
        )
        from dataclasses import asdict

        await ctx.send_message(json.dumps(asdict(approved_result)))


class Generator(Executor):
    """Generator that yields the final approved response."""

    def __init__(self) -> None:
        super().__init__(id="generator")

    @handler
    async def respond(self, message: str, ctx: WorkflowContext[str, str]) -> None:
        data = json.loads(message)
        result = ExecutionResult(**data)
        if result.approved:
            await ctx.yield_output(result.content)


class EchoTool(Executor):
    """Toy tool-agent used to populate the default catalog."""

    def __init__(self, id: str = "echo_tool") -> None:
        super().__init__(id=id)

    @handler
    async def invoke(
        self, payload: Mapping[str, Any], ctx: WorkflowContext[Mapping[str, Any], str]
    ) -> None:
        text = payload.get("query") or payload.get("input") or ""
        await ctx.yield_output(str(text))


def create_default_dynamic_participants(
    *, include_tool_agents: bool = True
) -> DynamicWorkflowParticipants:
    """Return the default participant factories used in legacy tests."""

    backbone: MutableMapping[str, ExecutorFactory] = {
        "planner": Planner,
        "executor": WorkerExecutor,
        "verifier": Verifier,
        "generator": Generator,
    }

    tools: MutableMapping[str, ExecutorFactory] = {}
    if include_tool_agents:
        tools["echo_tool"] = EchoTool

    return DynamicWorkflowParticipants(backbone=backbone, tools=tools)


def _coerce_participants(
    participants: DynamicWorkflowParticipants | Mapping[str, Mapping[str, ExecutorFactory]],
) -> DynamicWorkflowParticipants:
    if isinstance(participants, DynamicWorkflowParticipants):
        return participants

    backbone = participants.get("backbone", {})
    tools = participants.get("tools", {})
    return DynamicWorkflowParticipants(backbone=backbone, tools=tools)


def create_dynamic_workflow(
    *,
    participants: (
        DynamicWorkflowParticipants | Mapping[str, Mapping[str, ExecutorFactory]] | None
    ) = None,
    include_default_tool_agents: bool = True,
    max_iterations: int = 8,
) -> Workflow:
    """Build a small workflow suitable for experimentation and tests."""

    spec = _coerce_participants(participants or create_default_dynamic_participants())

    if include_default_tool_agents and not spec.tools:
        spec = spec.with_tool_agents(create_default_dynamic_participants().tools)

    planner = spec.backbone.get("planner", Planner)()
    worker = spec.backbone.get("executor", WorkerExecutor)()
    verifier = spec.backbone.get("verifier", Verifier)()
    generator = spec.backbone.get("generator", Generator)()

    builder = WorkflowBuilder(max_iterations=max_iterations)
    builder.set_start_executor(planner)
    builder.add_chain([planner, worker, verifier, generator])

    workflow = builder.build()

    # Expose participants on the workflow for observability and tests.
    setattr(workflow, "participants", spec.as_dict())
    return workflow


__all__ = [
    "DynamicWorkflowParticipants",
    "create_default_dynamic_participants",
    "create_dynamic_workflow",
]
