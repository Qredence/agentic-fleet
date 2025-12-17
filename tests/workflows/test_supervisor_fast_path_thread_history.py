from typing import Any, cast

import pytest
from agent_framework._types import ChatMessage, Role
from agent_framework._workflows import WorkflowOutputEvent

from agentic_fleet.workflows.config import WorkflowConfig
from agentic_fleet.workflows.context import SupervisorContext
from agentic_fleet.workflows.supervisor import SupervisorWorkflow


class _StubReasoner:
    def __init__(self) -> None:
        self.simple_calls: list[str] = []

    def generate_simple_response(self, task: str) -> str:
        self.simple_calls.append(task)
        return f"simple:{task}"


class _DummyWorkflowRunner:
    def __init__(self) -> None:
        self.called = False

    async def run_stream(self, message: object, **_: object):
        self.called = True
        yield WorkflowOutputEvent(
            data=[ChatMessage(role=Role.ASSISTANT, text="workflow:ok")],
            source_executor_id="dummy",
        )


class _ThreadWithLen:
    def __init__(self, n: int) -> None:
        self._n = n

    def __len__(self) -> int:
        return self._n


class _ThreadWithMessageStore:
    """Simulates agent-framework AgentThread history via message_store.messages."""

    def __init__(self, n: int) -> None:
        self.message_store = type("_Store", (), {"messages": [object()] * n})()


@pytest.mark.asyncio
async def test_fast_path_disabled_when_thread_has_history_streaming() -> None:
    """Follow-up turns must not use stateless fast-path (would ignore history)."""

    reasoner = _StubReasoner()
    runner = _DummyWorkflowRunner()
    context = SupervisorContext(config=WorkflowConfig(), dspy_supervisor=cast(Any, reasoner))
    workflow = SupervisorWorkflow(context, cast(Any, runner))

    thread = _ThreadWithLen(1)

    _ = [event async for event in workflow.run_stream("hi", thread=cast(Any, thread))]

    assert reasoner.simple_calls == []
    assert runner.called is True


@pytest.mark.asyncio
async def test_fast_path_still_applies_without_thread_history_streaming() -> None:
    """First turns (or no history) can still take the fast-path."""

    reasoner = _StubReasoner()
    runner = _DummyWorkflowRunner()
    context = SupervisorContext(config=WorkflowConfig(), dspy_supervisor=cast(Any, reasoner))
    workflow = SupervisorWorkflow(context, cast(Any, runner))

    thread = _ThreadWithLen(0)

    events = [event async for event in workflow.run_stream("hi", thread=cast(Any, thread))]

    assert reasoner.simple_calls == ["hi"]
    assert runner.called is False

    # Sanity: ensure we yielded at least one output-like event.
    assert any(isinstance(e, WorkflowOutputEvent) for e in events)


@pytest.mark.asyncio
async def test_fast_path_disabled_when_thread_has_message_store_history_streaming() -> None:
    """agent-framework AgentThread does not implement __len__; detect history via message_store."""

    reasoner = _StubReasoner()
    runner = _DummyWorkflowRunner()
    context = SupervisorContext(config=WorkflowConfig(), dspy_supervisor=cast(Any, reasoner))
    workflow = SupervisorWorkflow(context, cast(Any, runner))

    thread = _ThreadWithMessageStore(1)

    _ = [event async for event in workflow.run_stream("hi", thread=cast(Any, thread))]

    assert reasoner.simple_calls == []
    assert runner.called is True
