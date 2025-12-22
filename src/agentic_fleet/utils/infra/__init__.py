"""Infrastructure submodule: telemetry, tracing, resilience, and logging.

This submodule provides an organized interface to infrastructure-related
utilities. All exports are backward-compatible with direct imports from
utils.telemetry, utils.tracing, utils.resilience, and utils.logger.

Note:
    This module re-exports all functionality from agentic_fleet.utils.infra.logging
    for backward compatibility. New code should prefer importing from
    agentic_fleet.utils.infra.logging directly.

Usage:
    from agentic_fleet.utils.infra import initialize_tracing, setup_logger
    # or
    from agentic_fleet.utils.tracing import initialize_tracing  # still works
    # or (preferred)
    from agentic_fleet.utils.infra.logging import initialize_tracing
"""

from __future__ import annotations

# Re-export everything from core.logging to maintain backward compatibility
from .logging import setup_logger
from .resilience import (
    RATE_LIMIT_EXCEPTIONS,
    async_call_with_retry,
    create_circuit_breaker,
    create_rate_limit_retry,
    external_api_retry,
    llm_api_retry,
    log_retry_attempt,
)
from .telemetry import (
    ExecutionMetrics,
    PerformanceTracker,
    configure_telemetry,
    optional_span,
)
from .tracing import (
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
