"""Infrastructure submodule: telemetry, tracing, resilience, and logging.

This submodule provides an organized interface to infrastructure-related
utilities. All exports are backward-compatible with direct imports from
utils.telemetry, utils.tracing, utils.resilience, and utils.logger.

Usage:
    from agentic_fleet.utils.infra import initialize_tracing, setup_logger
    # or
    from agentic_fleet.utils.tracing import initialize_tracing  # still works
"""

from __future__ import annotations

from agentic_fleet.utils.logger import setup_logger
from agentic_fleet.utils.resilience import (
    RATE_LIMIT_EXCEPTIONS,
    async_call_with_retry,
    create_circuit_breaker,
    create_rate_limit_retry,
    external_api_retry,
    llm_api_retry,
    log_retry_attempt,
)
from agentic_fleet.utils.telemetry import (
    ExecutionMetrics,
    PerformanceTracker,
    configure_telemetry,
    optional_span,
)
from agentic_fleet.utils.tracing import (
    get_meter,
    get_tracer,
    initialize_tracing,
    reset_tracing,
)

__all__ = [
    "RATE_LIMIT_EXCEPTIONS",
    "ExecutionMetrics",
    "PerformanceTracker",
    "async_call_with_retry",
    "configure_telemetry",
    "create_circuit_breaker",
    "create_rate_limit_retry",
    "external_api_retry",
    "get_meter",
    "get_tracer",
    "initialize_tracing",
    "llm_api_retry",
    "log_retry_attempt",
    "optional_span",
    "reset_tracing",
    "setup_logger",
]
