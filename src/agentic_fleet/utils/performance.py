"""Performance monitoring utilities with structured logging and request correlation.

Provides:
- @async_timer decorator for tracking async function execution time
- CorrelationContext for request tracing across async boundaries
- Structured DEBUG logging for observability
"""

from __future__ import annotations

import functools
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

# Context variable for request correlation tracking
_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    """Get the current correlation ID from context.

    Returns:
        Current correlation ID or None if not set
    """
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set correlation ID in context.

    Args:
        correlation_id: Correlation ID to set. If None, generates new UUID4.

    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    _correlation_id_var.set(correlation_id)
    return correlation_id


def clear_correlation_id() -> None:
    """Clear correlation ID from context."""
    _correlation_id_var.set(None)


# Type variables for async_timer decorator
T = TypeVar("T")
P = ParamSpec("P")


def async_timer(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """Decorator to time async function execution with structured logging.

    Logs execution time with structured fields for observability:
    - event: "perf"
    - function: function name
    - duration_ms: execution time in milliseconds
    - correlation_id: request correlation ID (if set)

    Args:
        func: Async function to decorate

    Returns:
        Decorated async function

    Example:
        @async_timer
        async def my_function():
            await asyncio.sleep(1)
    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start_time = time.perf_counter()
        correlation_id = get_correlation_id()

        # Execute function
        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log with structured context
            logger.debug(
                "Function executed",
                extra={
                    "event": "perf",
                    "function": f"{func.__module__}.{func.__qualname__}",
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": correlation_id,
                    "status": "success",
                },
            )
            return result
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Function failed",
                extra={
                    "event": "perf",
                    "function": f"{func.__module__}.{func.__qualname__}",
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": correlation_id,
                    "status": "error",
                    "error": str(e),
                },
            )
            raise

    return wrapper


class PerformanceTracker:
    """Context manager for tracking operation performance with structured logging.

    Example:
        async with PerformanceTracker("database_query", context={"table": "users"}):
            result = await db.query("SELECT * FROM users")
    """

    def __init__(
        self,
        operation_name: str,
        *,
        context: dict[str, Any] | None = None,
        log_level: int = logging.DEBUG,
    ) -> None:
        """Initialize performance tracker.

        Args:
            operation_name: Name of the operation being tracked
            context: Additional context to include in logs
            log_level: Logging level (default: DEBUG)
        """
        self.operation_name = operation_name
        self.context = context or {}
        self.log_level = log_level
        self.start_time: float | None = None
        self.correlation_id: str | None = None

    async def __aenter__(self) -> PerformanceTracker:
        """Enter context: start timing and capture correlation ID."""
        self.start_time = time.perf_counter()
        self.correlation_id = get_correlation_id()
        logger.log(
            self.log_level,
            f"Starting operation: {self.operation_name}",
            extra={
                "event": "perf_start",
                "operation": self.operation_name,
                "correlation_id": self.correlation_id,
                **self.context,
            },
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context: log timing and status."""
        if self.start_time is None:
            return

        duration_ms = (time.perf_counter() - self.start_time) * 1000
        status = "error" if exc_type is not None else "success"

        log_data = {
            "event": "perf_end",
            "operation": self.operation_name,
            "duration_ms": round(duration_ms, 2),
            "correlation_id": self.correlation_id,
            "status": status,
            **self.context,
        }

        if exc_type is not None:
            log_data["error"] = str(exc_val)
            logger.error(
                f"Operation failed: {self.operation_name}",
                extra=log_data,
            )
        else:
            logger.log(
                self.log_level,
                f"Operation completed: {self.operation_name}",
                extra=log_data,
            )


class CorrelationContext:
    """Context manager for setting correlation ID scope.

    Example:
        async with CorrelationContext() as correlation_id:
            await my_async_function()  # Has access to correlation_id
    """

    def __init__(self, correlation_id: str | None = None) -> None:
        """Initialize correlation context.

        Args:
            correlation_id: Correlation ID to use. If None, generates new UUID4.
        """
        self.correlation_id = correlation_id
        self.previous_id: str | None = None

    async def __aenter__(self) -> str:
        """Enter context: set correlation ID."""
        self.previous_id = get_correlation_id()
        self.correlation_id = set_correlation_id(self.correlation_id)
        return self.correlation_id

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context: restore previous correlation ID."""
        if self.previous_id is not None:
            set_correlation_id(self.previous_id)
        else:
            clear_correlation_id()
