from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable, Generator
from typing import Any
from unittest.mock import patch

import pytest

from agentic_fleet.agents.coordinator import AgentFactory
from agentic_fleet.api.exceptions import AgentInitializationError

BASE_CONFIG: dict[str, Any] = {
    "model": "gpt-4o-mini",
    "instructions": "Test instructions for lifecycle coverage.",
}


class DummyLifecycleAgent:
    """Lightweight AgentLifecycle implementation used for factory tests."""

    def __init__(
        self,
        warmup_impl: Callable[[], Any] | Callable[[], Awaitable[Any]] | None = None,
        teardown_impl: Callable[[], Any] | Callable[[], Awaitable[Any]] | None = None,
    ) -> None:
        self._warmup_impl = warmup_impl or (lambda: None)
        self._teardown_impl = teardown_impl or (lambda: None)
        self.warmup_calls = 0
        self.teardown_calls = 0

    def warmup(self) -> Any:
        self.warmup_calls += 1
        return self._warmup_impl()

    def teardown(self) -> Any:
        self.teardown_calls += 1
        return self._teardown_impl()


@pytest.fixture(autouse=True)
def ensure_api_key() -> Generator[None, None, None]:
    """Guarantee OPENAI_API_KEY is available for tests.

    Annotated with explicit ``Generator`` return type so static analyzers
    recognize the fixture as a generator-based fixture instead of a function
    incorrectly typed as returning ``None``.
    """
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        yield


def _patch_chat_agent(agent: DummyLifecycleAgent):  # -> patch (runtime object, avoid type expr)
    """Patch ChatAgent constructor to return the provided dummy instance."""

    def _factory(*_args: Any, **_kwargs: Any) -> DummyLifecycleAgent:
        return agent

    return patch("agentic_fleet.agents.coordinator.ChatAgent", side_effect=_factory)


def _patch_openai_client():  # -> patch (runtime object, avoid type expr)
    """Patch OpenAIResponsesClient to avoid real client construction."""

    return patch("agentic_fleet.agents.coordinator.OpenAIResponsesClient", autospec=True)


def test_create_agent_invokes_warmup() -> None:
    agent = DummyLifecycleAgent()

    with _patch_openai_client(), _patch_chat_agent(agent):
        factory = AgentFactory()
        factory.create_agent("planner", BASE_CONFIG)

    assert agent.warmup_calls == 1, "warmup should be executed exactly once on creation"
    assert agent.teardown_calls == 0, "teardown should not run during creation"


def test_teardown_agent_invokes_registered_teardown() -> None:
    agent = DummyLifecycleAgent()

    with _patch_openai_client(), _patch_chat_agent(agent):
        factory = AgentFactory()
        factory.create_agent("planner", BASE_CONFIG)

    factory.teardown_agent("PlannerAgent")

    assert agent.teardown_calls == 1, "teardown should run when teardown_agent is invoked"


def test_warmup_failure_raises_agent_initialization_error() -> None:
    def boom() -> None:
        raise RuntimeError("warmup exploded")

    agent = DummyLifecycleAgent(warmup_impl=boom)

    with _patch_openai_client(), _patch_chat_agent(agent):
        factory = AgentFactory()
        with pytest.raises(AgentInitializationError, match="warmup exploded"):
            factory.create_agent("planner", BASE_CONFIG)

    factory.teardown_agent("PlannerAgent")  # should be a no-op because hook was never registered


@pytest.mark.asyncio
async def test_async_hooks_supported() -> None:
    async def async_warmup() -> None:
        await asyncio.sleep(0)

    async def async_teardown() -> None:
        await asyncio.sleep(0)

    agent = DummyLifecycleAgent(warmup_impl=async_warmup, teardown_impl=async_teardown)

    with _patch_openai_client(), _patch_chat_agent(agent):
        factory = AgentFactory()
        factory.create_agent("planner", BASE_CONFIG)

    assert agent.warmup_calls == 1
    await asyncio.sleep(0)  # ensure async warmup coroutine fully resolved

    factory.teardown_agent("PlannerAgent")
    await asyncio.sleep(0)

    assert agent.teardown_calls == 1
