"""
OpenTelemetry tracing configuration for AgenticFleet.

This module provides centralized tracing setup using the Agent Framework's
built-in observability support. Traces are exported to an OpenTelemetry collector
(default: localhost:4317 for AI Toolkit integration).

Usage:
    from agenticfleet.observability import setup_tracing
    setup_tracing()  # Uses default settings

    # Or with custom configuration
    setup_tracing(
        otlp_endpoint="http://custom-collector:4317",
        enable_sensitive_data=False
    )
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Global flag to track if tracing has been initialized
_tracing_initialized = False


def setup_tracing(
    otlp_endpoint: str | None = None,
    enable_sensitive_data: bool = True,
    **kwargs: Any,
) -> None:
    """
    Initialize OpenTelemetry tracing for AgenticFleet.

    This function sets up distributed tracing using the Agent Framework's
    observability module, which automatically instruments:
    - Chat client calls (OpenAI, Azure OpenAI, etc.)
    - Agent operations (run, run_stream)
    - Workflow execution (builder, executors, handlers)
    - Message processing and tool calls

    Args:
        otlp_endpoint: OTLP gRPC endpoint for the collector.
                      Defaults to http://localhost:4317 (AI Toolkit).
                      Can also be set via OTLP_ENDPOINT env var.
        enable_sensitive_data: Whether to capture prompts and completions
                              in traces. Disable in production for privacy.
                              Defaults to True (useful for debugging).
        **kwargs: Additional configuration passed to setup_observability.

    Environment Variables:
        OTLP_ENDPOINT: Override default OTLP collector endpoint
        TRACING_ENABLED: Set to "false" to disable tracing entirely
        ENABLE_SENSITIVE_DATA: Set to "false" to disable prompt/completion capture

    Example:
        # Development setup with AI Toolkit
        setup_tracing()

        # Production setup with custom collector
        setup_tracing(
            otlp_endpoint="http://jaeger-collector:4317",
            enable_sensitive_data=False
        )

    Note:
        This function is idempotent - calling it multiple times is safe.
        Only the first call will initialize tracing.
    """
    global _tracing_initialized

    if _tracing_initialized:
        logger.debug("Tracing already initialized, skipping")
        return

    # Check if tracing is explicitly disabled
    if os.getenv("TRACING_ENABLED", "true").lower() == "false":
        logger.info("Tracing disabled via TRACING_ENABLED environment variable")
        return

    # Resolve configuration from environment or defaults
    otlp_endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT", "http://localhost:4317")

    # Allow overriding sensitive data via environment
    env_sensitive = os.getenv("ENABLE_SENSITIVE_DATA")
    if env_sensitive is not None:
        enable_sensitive_data = env_sensitive.lower() != "false"

    try:
        from agent_framework.observability import setup_observability

        logger.info(f"Initializing OpenTelemetry tracing with endpoint: {otlp_endpoint}")
        logger.info(f"Sensitive data capture: {'enabled' if enable_sensitive_data else 'disabled'}")

        setup_observability(
            otlp_endpoint=otlp_endpoint,
            enable_sensitive_data=enable_sensitive_data,
            **kwargs,
        )
        logger.info("OpenTelemetry tracing initialized successfully")

    except ImportError as e:
        logger.warning(
            f"Could not initialize tracing: {e}. "
            "Install opentelemetry dependencies if tracing is needed."
        )
    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}", exc_info=True)
        # Don't raise - tracing should be optional and not break the application


def is_tracing_enabled() -> bool:
    """
    Check if tracing has been successfully initialized.

    Returns:
        bool: True if tracing is active, False otherwise.
    """
    return _tracing_initialized


def get_trace_config() -> dict[str, Any]:
    """
    Get current tracing configuration.

    Returns:
        dict: Configuration dictionary including endpoint and settings.
    """
    return {
        "enabled": _tracing_initialized,
        "otlp_endpoint": os.getenv("OTLP_ENDPOINT", "http://localhost:4317"),
        "sensitive_data_enabled": os.getenv("ENABLE_SENSITIVE_DATA", "true").lower() != "false",
    }
