"""Provider interface definitions for context/memory."""

from __future__ import annotations

from typing import Any, Protocol


class MemoryProvider(Protocol):
    def add(self, key: str, value: Any) -> None: ...

    def query(self, query: str) -> list[Any]: ...
