"""Performance profiling and monitoring utilities.

This module provides tools for tracking and logging slow operations in AgenticFleet.
"""

from __future__ import annotations

import inspect
import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@contextmanager
def timed_operation(
    operation_name: str,
    threshold_ms: float = 100.0,
    log_level: int = logging.WARNING,
):
    """Context manager to log slow operations.

    Measures the time taken by a block of code and logs a warning if it exceeds
    the threshold. Always logs debug info about the operation timing.

    Args:
        operation_name: Descriptive name for the operation
        threshold_ms: Threshold in milliseconds above which to log a warning
        log_level: Log level to use when threshold is exceeded (default: WARNING)

    Example:
        >>> with timed_operation("load_config", threshold_ms=50):
        ...     config = load_config()

    Yields:
        None
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms > threshold_ms:
            logger.log(
                log_level,
                f"Slow operation: {operation_name} took {elapsed_ms:.1f}ms "
                f"(threshold: {threshold_ms:.1f}ms)",
            )
        else:
            logger.debug(f"{operation_name} completed in {elapsed_ms:.1f}ms")


def profile_function(threshold_ms: float = 100.0) -> Callable[[F], F]:
    """Decorator to profile function execution time.

    Wraps a function to automatically log execution time if it exceeds the threshold.
    Works with both synchronous and asynchronous functions.

    Args:
        threshold_ms: Threshold in milliseconds above which to log a warning

    Returns:
        Decorated function

    Example:
        >>> @profile_function(threshold_ms=200)
        ... def expensive_operation():
        ...     # do work
        ...     pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with timed_operation(func.__name__, threshold_ms=threshold_ms):
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            with timed_operation(func.__name__, threshold_ms=threshold_ms):
                return await func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


class PerformanceTracker:
    """Track performance metrics across operations.

    Example:
        >>> tracker = PerformanceTracker()
        >>> with tracker.track("operation_name"):
        ...     # do work
        ...     pass
        >>> stats = tracker.get_stats("operation_name")
        >>> print(f"Average: {stats['avg_ms']:.1f}ms")
    """

    def __init__(self) -> None:
        """Initialize the performance tracker."""
        self._operations: dict[str, list[float]] = {}

    @contextmanager
    def track(self, operation_name: str):
        """Track an operation's performance.

        Args:
            operation_name: Name of the operation to track

        Yields:
            None
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            if operation_name not in self._operations:
                self._operations[operation_name] = []
            self._operations[operation_name].append(elapsed_ms)
            logger.debug(f"{operation_name}: {elapsed_ms:.1f}ms")

    def get_stats(self, operation_name: str) -> dict[str, float]:
        """Get statistics for a tracked operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Dictionary with min, max, avg, and count statistics
        """
        if operation_name not in self._operations:
            return {"min_ms": 0.0, "max_ms": 0.0, "avg_ms": 0.0, "count": 0}

        timings = self._operations[operation_name]
        return {
            "min_ms": min(timings),
            "max_ms": max(timings),
            "avg_ms": sum(timings) / len(timings),
            "count": len(timings),
        }

    def get_all_stats(self) -> dict[str, dict[str, float]]:
        """Get statistics for all tracked operations.

        Returns:
            Dictionary mapping operation names to their statistics
        """
        return {name: self.get_stats(name) for name in self._operations}

    def reset(self, operation_name: str | None = None) -> None:
        """Reset tracked statistics.

        Args:
            operation_name: Optional operation name to reset. If None, resets all.
        """
        if operation_name is None:
            self._operations.clear()
        else:
            self._operations.pop(operation_name, None)

    def log_summary(self, log_level: int = logging.INFO) -> None:
        """Log a summary of all tracked operations.

        Args:
            log_level: Log level to use for the summary
        """
        if not self._operations:
            logger.log(log_level, "No performance data tracked")
            return

        logger.log(log_level, "Performance Summary:")
        for name, stats in self.get_all_stats().items():
            logger.log(
                log_level,
                f"  {name}: avg={stats['avg_ms']:.1f}ms, "
                f"min={stats['min_ms']:.1f}ms, max={stats['max_ms']:.1f}ms, "
                f"count={int(stats['count'])}",
            )


# Global tracker instance for convenience
_global_tracker = PerformanceTracker()


def track_operation(operation_name: str):
    """Track an operation using the global tracker.

    Args:
        operation_name: Name of the operation to track

    Example:
        >>> with track_operation("my_operation"):
        ...     # do work
        ...     pass
    """
    return _global_tracker.track(operation_name)


def get_performance_stats(operation_name: str | None = None) -> dict[str, Any]:
    """Get performance statistics from the global tracker.

    Args:
        operation_name: Optional operation name. If None, returns all stats.

    Returns:
        Statistics dictionary
    """
    if operation_name is None:
        return _global_tracker.get_all_stats()
    return _global_tracker.get_stats(operation_name)


def log_performance_summary(log_level: int = logging.INFO) -> None:
    """Log a summary of global performance stats.

    Args:
        log_level: Log level to use for the summary
    """
    _global_tracker.log_summary(log_level)


def reset_performance_stats(operation_name: str | None = None) -> None:
    """Reset global performance statistics.

    Args:
        operation_name: Optional operation name. If None, resets all.
    """
    _global_tracker.reset(operation_name)
