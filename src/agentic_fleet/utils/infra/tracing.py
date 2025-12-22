"""Tracing initialization helpers using Microsoft Agent Framework observability.

This module configures OpenTelemetry tracing using the official Agent Framework
`setup_observability` function. Tracing is optional and activates based on:
  * Environment variable ENABLE_OTEL=true (recommended)
  * Or legacy TRACING_ENABLED=true

Supports multiple export destinations (can be enabled simultaneously):
  * Local OTLP collector via HTTP (Aspire Dashboard, etc.) - preferred for compatibility
  * Local OTLP collector via gRPC (AI Toolkit, Jaeger, etc.)
  * Azure Monitor / Application Insights (for Microsoft AI Foundry)
  * VS Code AI Toolkit extension

Environment variables (official Agent Framework naming):
  ENABLE_OTEL=true|false (default: false) - Master switch for tracing
  ENABLE_SENSITIVE_DATA=true|false (default: false) - Capture prompts/completions
  OTLP_ENDPOINT=http://localhost:4317 - Local OTLP gRPC collector endpoint
  OTLP_HTTP_ENDPOINT=http://localhost:4318/v1/traces - Local OTLP HTTP endpoint (Aspire)
  APPLICATIONINSIGHTS_CONNECTION_STRING - Azure Monitor/AI Foundry export
  VS_CODE_EXTENSION_PORT=4317 - AI Toolkit VS Code extension port

Legacy environment variables (still supported for backwards compatibility):
  TRACING_ENABLED=true|false
  TRACING_SENSITIVE_DATA=true|false
  APPLICATION_INSIGHTS_CONNECTION_STRING
  OTEL_EXPORTER_OTLP_ENDPOINT - standard OpenTelemetry env var

See: https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-observability

Safe to call multiple times; subsequent calls are no-ops.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_INITIALIZED = False


_DEFAULT_OTLP_GRPC_ENDPOINT = "http://localhost:4317"


def _env_bool(name: str, default: bool) -> bool:
    """Read boolean from environment variable."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def _get_connection_string() -> str | None:
    """Get Application Insights connection string from environment.

    Checks both official and alternative naming conventions.
    """
    # Remove quotes if present (common .env file issue)
    conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING") or os.getenv(
        "APPLICATION_INSIGHTS_CONNECTION_STRING"
    )
    if conn_str:
        return conn_str.strip().strip('"').strip("'")
    return None


def initialize_tracing(config: dict[str, Any] | None = None) -> bool:
    """Initialize tracing using Agent Framework's setup_observability.

    Uses the official Agent Framework observability setup which supports:
    - Azure Monitor/AI Foundry export (via APPLICATIONINSIGHTS_CONNECTION_STRING)
    - Local OTLP export (via OTLP_ENDPOINT)
    - VS Code AI Toolkit extension (via VS_CODE_EXTENSION_PORT)
    - Sensitive data capture control (via ENABLE_SENSITIVE_DATA)

    All exports can be enabled simultaneously for dual/triple export.

    Args:
        config: Loaded YAML config dictionary (optional, for legacy support).

    Returns:
        bool indicating whether tracing was successfully initialized/enabled.
    """
    global _INITIALIZED
    if _INITIALIZED:
        return True

    cfg_tracing = (config or {}).get("tracing", {}) if isinstance(config, dict) else {}

    # Explicit opt-out via env wins (even if other toggles are on)
    if "TRACING_ENABLED" in os.environ and not _env_bool("TRACING_ENABLED", False):
        logger.debug("Tracing explicitly disabled via TRACING_ENABLED env")
        return False
    if "ENABLE_OTEL" in os.environ and not _env_bool("ENABLE_OTEL", False):
        logger.debug("Tracing explicitly disabled via ENABLE_OTEL env")
        return False

    # Check if tracing is enabled (support both new and legacy env var names)
    enabled = (
        _env_bool("ENABLE_OTEL", False)
        or _env_bool("TRACING_ENABLED", False)
        or bool(cfg_tracing.get("enabled", False))
    )
    if not enabled:
        logger.debug("Tracing disabled (no enable flags set)")
        return False

    # Get configuration from environment or config
    enable_sensitive_data = _env_bool("ENABLE_SENSITIVE_DATA", False) or _env_bool(
        "TRACING_SENSITIVE_DATA", bool(cfg_tracing.get("capture_sensitive", False))
    )

    # Prefer the standard OpenTelemetry env var when present, so tests and local
    # developer environments behave predictably even if OTLP_ENDPOINT is set.
    otlp_endpoint = (
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.getenv("OTLP_ENDPOINT")
        or cfg_tracing.get("otlp_endpoint")
    )

    connection_string = _get_connection_string() or cfg_tracing.get(
        "azure_monitor_connection_string"
    )

    vs_code_port = os.getenv("VS_CODE_EXTENSION_PORT")
    vs_code_port_int = int(vs_code_port) if vs_code_port else None

    # Suppress noisy OpenTelemetry export errors (including UNIMPLEMENTED for metrics on Jaeger)
    logging.getLogger("opentelemetry.exporter.otlp.proto.grpc.exporter").setLevel(logging.CRITICAL)
    logging.getLogger("opentelemetry.exporter.otlp.proto.http.exporter").setLevel(logging.CRITICAL)
    logging.getLogger("opentelemetry.sdk._logs._internal").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry.sdk.metrics").setLevel(logging.WARNING)

    # Check for HTTP OTLP endpoint (preferred for Aspire Dashboard compatibility)
    otlp_http_endpoint = os.getenv("OTLP_HTTP_ENDPOINT") or cfg_tracing.get("otlp_http_endpoint")

    # Best-practice default for local development / VS Code AI Toolkit is gRPC on 4317.
    # If tracing is enabled but no endpoint was configured, fall back to localhost.
    if not otlp_endpoint:
        otlp_endpoint = _DEFAULT_OTLP_GRPC_ENDPOINT

    # Primary: Use Agent Framework's built-in observability setup
    try:
        from agent_framework.observability import setup_observability

        # Build kwargs dynamically based on what's configured
        kwargs: dict[str, Any] = {"enable_sensitive_data": enable_sensitive_data}

        if otlp_endpoint:
            kwargs["otlp_endpoint"] = otlp_endpoint

        if connection_string:
            kwargs["applicationinsights_connection_string"] = connection_string

        if vs_code_port_int:
            kwargs["vs_code_extension_port"] = vs_code_port_int

        setup_observability(**kwargs)

        # Log what was configured
        destinations = []
        if otlp_endpoint:
            destinations.append(f"OTLP({otlp_endpoint})")
        if connection_string:
            destinations.append("Azure Monitor/AI Foundry")
        if vs_code_port_int:
            destinations.append(f"VS Code AI Toolkit(port={vs_code_port_int})")

        logger.info(
            "Tracing initialized via agent_framework.observability → %s (sensitive_data=%s)",
            ", ".join(destinations) if destinations else "default exporters",
            enable_sensitive_data,
        )
        _INITIALIZED = True

        # Also set up HTTP exporter for Aspire Dashboard if configured
        if otlp_http_endpoint:
            _add_http_exporter(otlp_http_endpoint)

        return True

    except ImportError as e:
        logger.warning(
            "agent_framework.observability not available: %s. "
            "Ensure agent-framework>=1.0.0b251120 is installed.",
            e,
        )
    except Exception as e:
        logger.warning("Failed to initialize Agent Framework observability: %s", e)

    # Fallback: Manual OpenTelemetry setup with both gRPC and HTTP exporters
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": "agentic-fleet"})
        provider = TracerProvider(resource=resource)

        exporters_added = []

        # Add HTTP exporter (preferred for Aspire compatibility)
        if otlp_http_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter as HTTPSpanExporter,
                )

                http_exporter = HTTPSpanExporter(endpoint=otlp_http_endpoint)
                provider.add_span_processor(BatchSpanProcessor(http_exporter))
                exporters_added.append(f"HTTP({otlp_http_endpoint})")
            except ImportError:
                logger.debug("HTTP OTLP exporter not available")

        # Add gRPC exporter
        grpc_endpoint = otlp_endpoint or "http://localhost:4317"
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter as GRPCSpanExporter,
            )

            grpc_exporter = GRPCSpanExporter(endpoint=grpc_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(grpc_exporter))
            exporters_added.append(f"gRPC({grpc_endpoint})")
        except ImportError:
            logger.debug("gRPC OTLP exporter not available")

        if exporters_added:
            trace.set_tracer_provider(provider)
            logger.info(
                "Tracing initialized with manual OpenTelemetry fallback → %s",
                ", ".join(exporters_added),
            )

            return True
        else:
            logger.warning("No OTLP exporters available")
            return False

    except Exception as e:
        logger.warning("Failed to initialize tracing (all methods failed): %s", e)
        return False


def _add_http_exporter(endpoint: str) -> bool:
    """Add HTTP OTLP exporter for Aspire Dashboard compatibility.

    Args:
        endpoint: HTTP OTLP endpoint (e.g., http://localhost:4318/v1/traces)

    Returns:
        True if exporter was added successfully.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = trace.get_tracer_provider()
        if isinstance(provider, TracerProvider):
            http_exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(http_exporter))
            logger.info("Added HTTP OTLP exporter for Aspire Dashboard → %s", endpoint)
            return True
    except Exception as e:
        logger.debug("Could not add HTTP OTLP exporter: %s", e)
    return False


def reset_tracing() -> None:
    """Reset internal tracing initialization state (test helper).

    Does not tear down any configured tracer provider; intended only for unit tests
    that need to simulate a fresh state for initialization logic.
    """
    global _INITIALIZED
    _INITIALIZED = False


def get_tracer(name: str = "agentic_fleet") -> Any:
    """Get a tracer instance for custom span creation.

    Uses Agent Framework's helper if available, otherwise falls back to OpenTelemetry API.

    Args:
        name: Instrumentation library name (default: agentic_fleet).

    Returns:
        OpenTelemetry Tracer instance.
    """
    try:
        from agent_framework.observability import get_tracer as af_get_tracer

        return af_get_tracer(name)
    except ImportError:
        from opentelemetry import trace

        return trace.get_tracer(name)


def get_meter(name: str = "agentic_fleet") -> Any:
    """Get a meter instance for custom metrics.

    Uses Agent Framework's helper if available, otherwise falls back to OpenTelemetry API.

    Args:
        name: Instrumentation library name (default: agentic_fleet).

    Returns:
        OpenTelemetry Meter instance.
    """
    try:
        from agent_framework.observability import get_meter as af_get_meter

        return af_get_meter(name)
    except ImportError:
        from opentelemetry import metrics

        return metrics.get_meter(name)


__all__ = ["get_meter", "get_tracer", "initialize_tracing", "reset_tracing"]
