"""Common agent interfaces and lifecycle contracts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

# Broaden lifecycle hook contract to accept any return type (awaitable or plain)
# since tests use dummy implementations returning arbitrary objects.
LifecycleHook = Callable[[], Awaitable[Any] | Any]


@runtime_checkable
class AgentLifecycle(Protocol):
    """Optional asynchronous lifecycle hooks for agents.

    Agents can implement one or both hooks. The factory will invoke :meth:`warmup`
    immediately after instantiation and cache :meth:`teardown` for later cleanup.
    """

    def warmup(self) -> Awaitable[Any] | Any: ...
    def teardown(self) -> Awaitable[Any] | Any: ...


__all__ = ["AgentLifecycle", "LifecycleHook"]
