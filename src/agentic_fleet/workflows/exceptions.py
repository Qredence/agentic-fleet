"""
Custom exceptions for workflow operations.

This module provides a comprehensive exception hierarchy for AgenticFleet,
enabling better error handling and debugging throughout the codebase.
"""

from __future__ import annotations

from typing import Any


class WorkflowError(Exception):
    """Base exception for workflow-related errors.

    All workflow exceptions inherit from this class, allowing for
    consistent error handling patterns.
    """

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        """Initialize workflow error.

        Args:
            message: Human-readable error message
            context: Optional context dictionary with additional error details
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        """Return formatted error message with context."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


class AgentExecutionError(WorkflowError):
    """Raised when an agent fails during execution."""

    def __init__(
        self,
        agent_name: str,
        task: str,
        original_error: Exception,
        context: dict[str, Any] | None = None,
    ):
        """Initialize agent execution error.

        Args:
            agent_name: Name of the agent that failed
            task: Task that was being executed
            original_error: The original exception that occurred
            context: Optional additional context
        """
        self.agent_name = agent_name
        self.task = task
        self.original_error = original_error
        error_context = {
            "agent": agent_name,
            "task_preview": task[:100] if len(task) > 100 else task,
            "error_type": type(original_error).__name__,
            **(context or {}),
        }
        super().__init__(
            f"Agent '{agent_name}' failed on task: {task[:100]}...",
            context=error_context,
        )


class RoutingError(WorkflowError):
    """Raised when task routing fails or produces invalid results."""

    def __init__(
        self,
        message: str,
        routing_decision: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize routing error.

        Args:
            message: Error message
            routing_decision: The routing decision that caused the error
            context: Optional additional context
        """
        self.routing_decision = routing_decision
        error_context = {
            "routing_decision": routing_decision,
            **(context or {}),
        }
        super().__init__(message, context=error_context)


class ConfigurationError(WorkflowError):
    """Raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_value: Any = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize configuration error.

        Args:
            message: Error message
            config_key: The configuration key that caused the error
            config_value: The invalid configuration value
            context: Optional additional context
        """
        self.config_key = config_key
        self.config_value = config_value
        error_context = {
            "config_key": config_key,
            "config_value": str(config_value) if config_value is not None else None,
            **(context or {}),
        }
        super().__init__(message, context=error_context)


class HistoryError(WorkflowError):
    """Raised when execution history operations fail."""

    def __init__(
        self,
        message: str,
        history_file: str | None = None,
        operation: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize history error.

        Args:
            message: Error message
            history_file: The history file that caused the error
            operation: The operation that failed (read, write, append, etc.)
            context: Optional additional context
        """
        self.history_file = history_file
        self.operation = operation
        error_context = {
            "history_file": history_file,
            "operation": operation,
            **(context or {}),
        }
        super().__init__(message, context=error_context)


class CompilationError(WorkflowError):
    """Raised when DSPy module compilation fails."""

    def __init__(
        self,
        message: str,
        module_name: str | None = None,
        optimizer: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize compilation error.

        Args:
            message: Error message
            module_name: Name of the module that failed to compile
            optimizer: The optimizer that was being used
            context: Optional additional context
        """
        self.module_name = module_name
        self.optimizer = optimizer
        error_context = {
            "module_name": module_name,
            "optimizer": optimizer,
            **(context or {}),
        }
        super().__init__(message, context=error_context)


class CacheError(WorkflowError):
    """Raised when cache operations fail."""

    def __init__(
        self,
        message: str,
        cache_key: str | None = None,
        operation: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize cache error.

        Args:
            message: Error message
            cache_key: The cache key that caused the error
            operation: The operation that failed (get, set, delete, etc.)
            context: Optional additional context
        """
        self.cache_key = cache_key
        self.operation = operation
        error_context = {
            "cache_key": cache_key,
            "operation": operation,
            **(context or {}),
        }
        super().__init__(message, context=error_context)


class ValidationError(WorkflowError):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize validation error.

        Args:
            message: Error message
            field: The field that failed validation
            value: The invalid value
            context: Optional additional context
        """
        self.field = field
        self.value = value
        error_context = {
            "field": field,
            "value": str(value) if value is not None else None,
            **(context or {}),
        }
        super().__init__(message, context=error_context)


class WorkflowTimeoutError(WorkflowError):
    """Raised when an operation times out."""

    def __init__(
        self,
        message: str,
        timeout_seconds: float | None = None,
        operation: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize timeout error.

        Args:
            message: Error message
            timeout_seconds: The timeout value that was exceeded
            operation: The operation that timed out
            context: Optional additional context
        """
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        error_context = {
            "timeout_seconds": timeout_seconds,
            "operation": operation,
            **(context or {}),
        }
        super().__init__(message, context=error_context)


class ToolError(WorkflowError):
    """Raised when tool execution fails."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize tool error.

        Args:
            message: Error message
            tool_name: Name of the tool that failed
            tool_args: Arguments that were passed to the tool
            context: Optional additional context
        """
        self.tool_name = tool_name
        self.tool_args = tool_args
        error_context = {
            "tool_name": tool_name,
            "tool_args": tool_args,
            **(context or {}),
        }
        super().__init__(message, context=error_context)
