"""Telemetry utilities for performance tracking and tracing.

Provides:
- optional_span: Lightweight span context manager for tracing
- PerformanceTracker: Track and analyze agent execution metrics
- MLflow integration utilities for DSPy + agent-framework observability

Replace with real OpenTelemetry integration when ENABLE_OTEL=true.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionMetrics:
    """Metrics for a single execution."""

    agent_name: str
    duration: float
    success: bool
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class PerformanceTracker:
    """Track and analyze agent execution performance.

    Usage:
        tracker = PerformanceTracker()
        tracker.record_execution(
            agent_name="ResearcherAgent",
            duration=12.5,
            success=True
        )
        stats = tracker.get_stats()
    """

    def __init__(self) -> None:
        """Initialize performance tracker."""
        self.executions: list[ExecutionMetrics] = []
        self.metrics_by_agent: dict[str, list[ExecutionMetrics]] = defaultdict(list)

    def record_execution(
        self,
        agent_name: str,
        duration: float,
        success: bool,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Record an agent execution.

        Args:
            agent_name: Name of the agent
            duration: Execution time in seconds
            success: Whether execution succeeded
            metadata: Optional execution metadata
            error: Optional error message if failed
        """
        metrics = ExecutionMetrics(
            agent_name=agent_name,
            duration=duration,
            success=success,
            metadata=metadata or {},
            error=error,
        )

        self.executions.append(metrics)
        self.metrics_by_agent[agent_name].append(metrics)

        # Log slow executions
        if duration > 30:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Slow execution: {agent_name} took {duration:.2f}s")

    def get_stats(self, agent_name: str | None = None) -> dict[str, Any]:
        """Get performance statistics.

        Args:
            agent_name: Optional agent name to filter by

        Returns:
            Dictionary with performance metrics
        """
        executions = self.metrics_by_agent.get(agent_name, []) if agent_name else self.executions

        if not executions:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0,
                "min_duration": 0.0,
                "max_duration": 0.0,
            }

        durations = [e.duration for e in executions]
        successes = sum(1 for e in executions if e.success)

        return {
            "total_executions": len(executions),
            "success_rate": successes / len(executions),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "recent_errors": [e.error for e in executions[-5:] if e.error],
        }

    def get_bottlenecks(self, threshold: float = 5.0) -> list[dict[str, Any]]:
        """Identify performance bottlenecks.

        Args:
            threshold: Duration threshold in seconds

        Returns:
            List of slow executions
        """
        bottlenecks = [
            {
                "agent": e.agent_name,
                "duration": e.duration,
                "timestamp": e.timestamp,
                "metadata": e.metadata,
            }
            for e in self.executions
            if e.duration > threshold
        ]

        return sorted(bottlenecks, key=lambda x: x["duration"], reverse=True)


@contextmanager
def optional_span(
    name: str,
    tracer_name: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """Yield a span if OpenTelemetry is available and configured.

    Args:
        name: Logical name of the traced operation.
        tracer_name: Name of tracer (defaults to module name).
        attributes: Optional mapping of attributes.
    """
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer(tracer_name or __name__)
        with tracer.start_as_current_span(name, attributes=attributes) as span:
            yield span
    except (ImportError, Exception):
        # OpenTelemetry not installed or tracing failed to init
        yield None


__all__ = ["ExecutionMetrics", "PerformanceTracker", "optional_span"]
