"""
Infrastructure utilities surface for caching, logging, resilience, telemetry, and tracing.

This module consolidates common operational helpers behind a single import path while
preserving the existing, granular modules.
"""

from __future__ import annotations

from .cache import CacheStats, TTLCache
from .logger import setup_logger
from .resilience import (
    async_call_with_retry,
    create_circuit_breaker,
    external_api_retry,
    log_retry_attempt,
)
from .telemetry import PerformanceTracker, optional_span
from .tracing import initialize_tracing

__all__ = [
    "CacheStats",
    "PerformanceTracker",
    "TTLCache",
    "async_call_with_retry",
    "create_circuit_breaker",
    "external_api_retry",
    "initialize_tracing",
    "log_retry_attempt",
    "optional_span",
    "setup_logger",
]
