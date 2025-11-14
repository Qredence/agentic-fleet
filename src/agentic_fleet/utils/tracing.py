"""Tracing initialization helpers.

This module configures OpenTelemetry tracing for the DSPy Agent Framework integration.
Tracing is optional and will only activate if either:
  * Config enables it (config.tracing.enabled) OR
  * Environment variable TRACING_ENABLED=true

When enabled we attempt to use the agent-framework's built-in observability helper
`setup_observability`. If unavailable (older version / missing dependency) we fall back
to a minimal OpenTelemetry OTLP exporter configuration so spans from custom
instrumentation (future) still emit.

Environment variables (all optional):
  OTEL_EXPORTER_OTLP_ENDPOINT (overrides config endpoint)
  OTEL_EXPORTER_OTLP_HEADERS
  TRACING_ENABLED=true|false
  TRACING_SENSITIVE_DATA=true|false (controls prompt/completion capture)

Safe to call multiple times; subsequent calls are no-ops.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_INITIALIZED = False


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def initialize_tracing(config: dict[str, Any] | None = None) -> bool:
    """Initialize tracing if enabled.

    Args:
        config: Loaded YAML config dictionary (optional).

    Returns:
        bool indicating whether tracing was successfully initialized/enabled.
    """
    global _INITIALIZED
    if _INITIALIZED:
        return True

    cfg_tracing = (config or {}).get("tracing", {}) if isinstance(config, dict) else {}
    enabled = _env_bool("TRACING_ENABLED", bool(cfg_tracing.get("enabled", False)))
    if not enabled:
        logger.debug("Tracing disabled (TRACING_ENABLED flag or config)")
        return False

    # Determine endpoint (env > config > default localhost)
    endpoint = (
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        or cfg_tracing.get("otlp_endpoint")
        or "http://localhost:4317"
    )

    capture_sensitive = _env_bool(
        "TRACING_SENSITIVE_DATA", bool(cfg_tracing.get("capture_sensitive", True))
    )

    # Suppress OpenTelemetry OTLP exporter errors (Jaeger doesn't support log export)
    logging.getLogger("opentelemetry.exporter.otlp.proto.grpc.exporter").setLevel(logging.CRITICAL)
    logging.getLogger("opentelemetry.sdk._logs._internal").setLevel(logging.CRITICAL)

    # First attempt: agent-framework helper
    try:
        from agent_framework.observability import (
            setup_observability,  # type: ignore
        )

        setup_observability(
            otlp_endpoint=endpoint,
            enable_sensitive_data=capture_sensitive,
        )
        logger.info(
            "Tracing initialized via agent_framework.observability (endpoint=%s)",
            endpoint,
        )
        _INITIALIZED = True
        return True
    except Exception as e:  # pragma: no cover - fallback path
        logger.debug("agent_framework.observability unavailable or failed: %s", e)

    # Fallback: manual minimal OpenTelemetry init
    try:  # pragma: no cover - minimal instrumentation path
        from opentelemetry import trace  # type: ignore
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,  # type: ignore
        )
        from opentelemetry.sdk.resources import Resource  # type: ignore
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,  # type: ignore
        )

        resource = Resource.create({"service.name": "dspy-agent-framework"})
        provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(provider)
        logger.info(
            "Tracing initialized with manual OpenTelemetry fallback (endpoint=%s)",
            endpoint,
        )
        _INITIALIZED = True
        return True
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to initialize tracing (both primary & fallback): %s", e)
        return False


def reset_tracing() -> None:
    """Reset internal tracing initialization state (test helper).

    Does not tear down any configured tracer provider; intended only for unit tests
    that need to simulate a fresh state for initialization logic.
    """
    global _INITIALIZED
    _INITIALIZED = False


__all__ = ["initialize_tracing", "reset_tracing"]
