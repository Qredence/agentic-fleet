"""Telemetry helpers for optional OpenTelemetry instrumentation."""

from __future__ import annotations

import os
from contextlib import AbstractContextManager, nullcontext
from functools import lru_cache
from typing import TYPE_CHECKING, Any

ENABLE_ENV_VAR = "ENABLE_OTEL"

try:
    from opentelemetry import metrics as _metrics_api
except Exception:  # pragma: no cover - optional dependency
    _metrics_api = None

try:
    from opentelemetry import trace as _trace_api
except Exception:  # pragma: no cover - optional dependency
    _trace_api = None

if TYPE_CHECKING:
    from opentelemetry.metrics import Counter
    from opentelemetry.trace import Span, Tracer

__all__ = [
    "ENABLE_ENV_VAR",
    "get_tracer",
    "metrics_enabled",
    "optional_span",
    "record_workflow_event",
    "telemetry_enabled",
    "tracing_enabled",
]


def telemetry_enabled() -> bool:
    """Return True when telemetry instrumentation is enabled via environment flag."""
    value = os.getenv(ENABLE_ENV_VAR, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def tracing_enabled() -> bool:
    """Return True when tracing can be emitted."""
    return telemetry_enabled() and _trace_api is not None


def metrics_enabled() -> bool:
    """Return True when metrics can be emitted."""
    return telemetry_enabled() and _metrics_api is not None


def get_tracer(name: str, *, version: str | None = None) -> Tracer | None:
    """Return an OpenTelemetry tracer for the supplied module name when available."""
    if not tracing_enabled() or _trace_api is None:
        return None
    return _trace_api.get_tracer(name, version)


def optional_span(
    span_name: str,
    *,
    tracer_name: str,
    **kwargs: Any,
) -> AbstractContextManager[Span | None]:
    """Return a context manager that yields an active span when tracing is enabled."""
    tracer = get_tracer(tracer_name)
    if tracer is None:
        return nullcontext(None)
    return tracer.start_as_current_span(span_name, **kwargs)  # type: ignore


@lru_cache(maxsize=1)
def _workflow_event_counter() -> Counter | None:
    """Return the workflow event counter, lazily creating it on first access."""
    if not metrics_enabled() or _metrics_api is None:
        return None

    meter = _metrics_api.get_meter("agentic_fleet.workflow")
    try:
        return meter.create_counter(
            name="agenticfleet.workflow.events",
            unit="1",
            description="Number of workflow events emitted by AgenticFleet workflows.",
        )
    except Exception:  # pragma: no cover - metric backend misconfiguration
        return None


def record_workflow_event(workflow_id: str, event_type: str | None = None) -> None:
    """Increment the workflow event counter when metrics are enabled."""
    counter = _workflow_event_counter()
    if counter is None:
        return

    attributes = {
        "workflow.id": workflow_id,
        "event.type": event_type or "unspecified",
    }

    try:
        counter.add(1, attributes=attributes)
    except Exception:  # pragma: no cover - metric backend misconfiguration
        # Metrics emission must never fail the workflow path.
        return
