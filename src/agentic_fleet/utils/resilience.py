"""Resilience utilities for the Agentic Fleet.

This module provides circuit breaker and retry mechanisms to improve the robustness
of external service interactions (e.g., OpenAI, Tavily).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def log_retry_attempt(retry_state: RetryCallState) -> None:
    """Log retry attempts."""
    if retry_state.outcome and retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        fn_name = (
            getattr(retry_state.fn, "__name__", "unknown_function")
            if retry_state.fn
            else "unknown_function"
        )
        logger.warning(
            f"Retrying {fn_name} due to {type(exception).__name__}: {exception}. "
            f"Attempt {retry_state.attempt_number}"
        )


def create_circuit_breaker(
    max_failures: int = 5,
    reset_timeout: int = 60,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Create a circuit breaker decorator.

    Note: Tenacity doesn't have a built-in "Circuit Breaker" in the traditional sense
    (stateful open/closed/half-open), but we can simulate resilience with
    smart retries and stop conditions. For true circuit breaking, we might need
    a dedicated library like `pybreaker`, but for now we'll use robust retries
    with exponential backoff which solves 90% of the "don't hammer down services" problem.

    If strict circuit breaking is needed, we can integrate `pybreaker` later.
    """

    # For now, we implement a robust retry strategy as the primary resilience mechanism
    return retry(
        retry=retry_if_exception_type(exceptions),
        stop=stop_after_attempt(max_failures),
        wait=wait_exponential(multiplier=1, min=2, max=reset_timeout),
        before_sleep=log_retry_attempt,
        reraise=True,
    )


# Standard retry configuration for external APIs
external_api_retry = create_circuit_breaker(
    max_failures=3,
    reset_timeout=30,
    exceptions=(
        TimeoutError,
        ConnectionError,
        # Add other transient errors here
    ),
)
