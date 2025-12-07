"""Tests for the middleware helpers in agentic_fleet.core."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

import dspy
import pytest

from agentic_fleet.core.middleware import BridgeConverter, BridgeMiddleware, ChatMiddleware
from agentic_fleet.utils.types import MessageLike


class DummyMessage(MessageLike):
    """Minimal MessageLike stub for BridgeConverter tests."""

    def __init__(self, role: str, content: str | list[DummyListItem] | list[str]):
        self._role = role
        self._content = content

    @property
    def role(self) -> str:
        return self._role

    @property
    def content(self) -> str | list[DummyListItem] | list[str]:
        return self._content


@dataclass
class DummyListItem:
    """Simple helper mimicking Azure SDK list items with text attributes."""

    text: str


class TestChatMiddlewareHooks:
    """Ensure the ChatMiddleware lifecycle hooks remain no-ops."""

    @pytest.mark.asyncio
    async def test_hooks_are_noops(self):
        middleware = ChatMiddleware()

        await middleware.on_start("task", {"workflowId": "wf-1"})
        await middleware.on_event({"progress": 42})
        await middleware.on_end("done")
        await middleware.on_error(RuntimeError("boom"))

        assert hasattr(middleware, "on_start")
        assert hasattr(middleware, "on_event")
        assert hasattr(middleware, "on_end")
        assert hasattr(middleware, "on_error")


class TestBridgeConverter:
    """Ensure message normalization handles the most common call sites."""

    def test_message_to_dict_returns_dict_unchanged(self):
        message = {"role": "user", "content": "Hello"}
        assert BridgeConverter.message_to_dict(message) == message

    def test_message_to_dict_handles_object_shapes(self):
        payload = DummyMessage(role="assistant", content="Done")
        normalized = BridgeConverter.message_to_dict(payload)
        assert normalized["role"] == "assistant"
        assert normalized["content"] == "Done"

    def test_message_to_dict_joins_list_content(self):
        payload = DummyMessage(
            role="assistant",
            content=[DummyListItem("a"), DummyListItem("b")],
        )
        normalized = BridgeConverter.message_to_dict(payload)
        assert normalized["content"] == "ab"

    def test_example_to_messages_emits_task(self):
        example = dspy.Example(task="final step", context="user: hi")
        messages = BridgeConverter.example_to_messages(example)
        assert isinstance(messages, list)
        assert messages[-1].text == "final step"


class DummyHistoryManager:
    """Simple helper that records async save calls."""

    def __init__(self):
        self.save_execution_async = AsyncMock()


@pytest.fixture
def history_manager():
    return DummyHistoryManager()


class TestBridgeMiddleware:
    """BridgeMiddleware should persist execution metadata when workflows end."""

    @pytest.mark.asyncio
    async def test_on_start_and_end_use_history_manager(self, history_manager):
        middleware = BridgeMiddleware(history_manager=history_manager, dspy_examples_path=None)

        await middleware.on_start("task", {"workflowId": "wf-1", "mode": "demo"})
        await middleware.on_end({"result": "done"})

        history_manager.save_execution_async.assert_awaited_once()
        saved = history_manager.save_execution_async.call_args.args[0]
        assert saved["task"] == "task"
        assert saved["workflowId"] == "wf-1"

    @pytest.mark.asyncio
    async def test_on_error_records_failure(self, history_manager):
        middleware = BridgeMiddleware(history_manager=history_manager, dspy_examples_path=None)

        await middleware.on_start("task", {"workflowId": "forty"})
        await middleware.on_error(RuntimeError("boom"))

        history_manager.save_execution_async.assert_awaited()
        saved = history_manager.save_execution_async.call_args.args[0]
        assert saved["status"] == "failed"
        assert saved["error"] == "boom"
