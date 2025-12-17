"""Core logging and observability for AgenticFleet.

This module provides unified logging and tracing capabilities, consolidating:
- Logger setup (from utils/logger.py)
- OpenTelemetry tracing (from utils/tracing.py)
- Telemetry/metrics (from utils/telemetry.py)
- Resilience/retry utilities (from utils/resilience.py)

Usage:
    from agentic_fleet.core.logging import setup_logger, initialize_tracing

    # Setup logger
    logger = setup_logger(__name__)
    logger.info("Hello world")

    # Initialize tracing (call once at startup)
    initialize_tracing()

    # Use optional spans
    with optional_span("my-operation") as span:
        # ... do work
        pass
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
