import pytest

from agentic_fleet.workflows.exceptions import AgentExecutionError
from agentic_fleet.workflows.strategies import (
    _extract_tool_usage,
    execute_delegated,
    execute_parallel,
    execute_sequential,
)


class StubAgent:
    """Minimal async agent stub."""

    def __init__(self, name: str, responses):
        self.name = name
        self._responses = iter(responses)

    async def run(self, task: str):
        value = next(self._responses)
        if isinstance(value, Exception):
            raise value
        return value


class ErrorAgent:
    async def run(self, task: str):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_execute_delegated_raises_for_missing_agent():
    with pytest.raises(AgentExecutionError):
        await execute_delegated({}, "missing", "task")


@pytest.mark.asyncio
async def test_execute_parallel_collects_results_and_skips_missing():
    agents = {
        "one": StubAgent("one", ["result-1"]),
        "two": StubAgent("two", ["result-2"]),
    }
    result, usage = await execute_parallel(agents, ["one", "two", "ghost"], ["t1", "t2", "t3"])

    assert result == "result-1\n\nresult-2"
    assert usage == []


@pytest.mark.asyncio
async def test_execute_parallel_handles_exceptions_without_crashing():
    agents = {
        "ok": StubAgent("ok", ["fine"]),
        "bad": ErrorAgent(),
    }
    result, _ = await execute_parallel(agents, ["ok", "bad"], ["x", "y"])

    assert "fine" in result
    assert "[bad failed:" in result


@pytest.mark.asyncio
async def test_execute_sequential_skips_unknown_agents_and_returns_last_result():
    agents = {
        "known": StubAgent("known", ["after-known"]),
    }
    result, usage = await execute_sequential(
        agents,
        ["unknown", "known"],
        task="start",
        enable_handoffs=False,
        handoff=None,
    )

    assert result == "after-known"
    assert usage == []


def test_extract_tool_usage_collects_all_locations():
    class Msg:
        def __init__(self):
            self.tool_calls = [{"name": "tc", "arguments": {"q": 1}}]
            self.additional_properties = {"tool_usage": [{"tool": "inner", "arguments": {}}]}
            self.timestamp = 123

    class Resp:
        def __init__(self):
            self.messages = [Msg()]
            self.additional_properties = {"tool_usage": [{"tool": "top", "arguments": {"a": 1}}]}

    usage = _extract_tool_usage(Resp())

    tools = {u["tool"] for u in usage}
    assert tools == {"tc", "inner", "top"}
