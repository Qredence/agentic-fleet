"""Type definitions and protocols for AgenticFleet.

This module provides protocol definitions and type stubs for external dependencies
to improve type safety and eliminate type: ignore comments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from .models import (
    AgentMessage,
    AgentRole,
    ExecutionMode,
    TaskResult,
    TaskStatus,
    ToolResult,
    WorkflowState,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from typing import TypeVar

    from azure.cosmos import DatabaseProxy

    T = TypeVar("T")


# DSPy Protocol Definitions
@runtime_checkable
class DSPySignature(Protocol):
    """Protocol for DSPy Signature classes."""

    def __call__(self, **kwargs: Any) -> Any:
        """Call the signature with inputs."""
        ...


@runtime_checkable
class DSPyModule(Protocol):
    """Protocol for DSPy modules."""

    def forward(self, **kwargs: Any) -> Any:
        """Forward pass through the module."""
        ...

    def __call__(self, **kwargs: Any) -> Any:
        """Call the module."""
        ...


@runtime_checkable
class DSPySettings(Protocol):
    """Protocol for DSPy settings configuration."""

    def configure(self, **kwargs: Any) -> None:
        """Configure DSPy settings."""
        ...


# Agent Framework Protocol Definitions
@runtime_checkable
class ChatClient(Protocol):
    """Protocol for chat clients."""

    async def create(self, **kwargs: Any) -> Any:
        """Create a chat completion."""
        ...


@runtime_checkable
class ChatClientWithExtraBody(Protocol):
    """Protocol for chat clients that support extra_body."""

    extra_body: dict[str, Any] | None
    _default_extra_body: dict[str, Any] | None
    _reasoning_effort: str | None
    async_client: Any | None


# Tool Protocol Extensions
@runtime_checkable
class ToolProtocol(Protocol):
    """Protocol for tools."""

    name: str
    description: str
    schema: dict[str, Any]

    async def run(self, **kwargs: Any) -> Any:
        """Run the tool with given arguments."""
        ...


# Progress Callback Protocol
@runtime_checkable
class ProgressCallback(Protocol):
    """Protocol for progress callbacks."""

    def on_start(self, message: str) -> None:
        """Called when an operation starts."""
        ...

    def on_progress(self, message: str) -> None:
        """Called to report progress."""
        ...

    def on_complete(self, message: str) -> None:
        """Called when an operation completes."""
        ...

    def on_error(self, message: str, error: Exception | None = None) -> None:
        """Called when an error occurs."""
        ...


# Cache Protocol
@runtime_checkable
class CacheProtocol(Protocol):
    """Protocol for cache implementations."""

    def get(self, key: str) -> Any | None:
        """Get a value from the cache."""
        ...

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value in the cache."""
        ...

    def delete(self, key: str) -> None:
        """Delete a value from the cache."""
        ...

    def clear(self) -> None:
        """Clear all cache entries."""
        ...


# History Manager Protocol
@runtime_checkable
class HistoryManagerProtocol(Protocol):
    """Protocol for history managers."""

    def append(self, execution: dict[str, Any]) -> None:
        """Append an execution to history."""
        ...

    def get_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent execution history."""
        ...

    def save(self) -> None:
        """
        Persist the manager's recorded history to durable storage.

        This flushes the in-memory execution history so it is retained outside the running process.
        """
        ...


# Azure Cosmos DB Protocol
@runtime_checkable
class CosmosClientProtocol(Protocol):
    """Protocol for Azure Cosmos DB client.

    This protocol defines the minimal interface needed for CosmosClient
    usage within AgenticFleet, enabling type-safe optional Cosmos integration.
    """

    def get_database_client(self, database: str) -> DatabaseProxy:
        """
        Obtain a client for the named Cosmos DB database.

        Parameters:
            database (str): The name of the database to retrieve a client for.

        Returns:
            DatabaseProxy: A database client instance connected to the specified database.
        """
        ...


# Message Protocol for chat/agent messages
@runtime_checkable
class MessageLike(Protocol):
    """Protocol for message-like objects.

    This protocol defines the minimal interface for message objects used
    in chat/agent workflows. Compatible with ChatMessage, ThreadMessage,
    and similar message types that expose role and content attributes.
    """

    @property
    def role(self) -> Any:
        """
        The role of the message sender.

        Returns:
            The sender's role (for example, 'user' or 'assistant').
        """
        ...

    @property
    def content(self) -> Any:
        """
        Expose the message's content.

        Returns:
            The message's content value (e.g., text, structured data, or media metadata).
        """
        ...


# Type aliases for common patterns
if TYPE_CHECKING:
    from agent_framework._agents import ChatAgent

    AgentDict = dict[str, ChatAgent]
    EventStream = AsyncIterator[Any]
    ExecutionResult = dict[str, Any]
    RoutingResult = dict[str, Any]
    JudgeResult = dict[str, Any]

__all__ = [
    "AgentMessage",
    "AgentRole",
    "CacheProtocol",
    "ChatClient",
    "ChatClientWithExtraBody",
    "CosmosClientProtocol",
    "DSPyModule",
    "DSPySettings",
    "DSPySignature",
    "ExecutionMode",
    "HistoryManagerProtocol",
    "MessageLike",
    "ProgressCallback",
    "TaskResult",
    "TaskStatus",
    "ToolProtocol",
    "ToolResult",
    "WorkflowState",
]
