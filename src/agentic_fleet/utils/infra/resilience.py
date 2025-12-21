"""Resilience utilities for the Agentic Fleet.

This module provides circuit breaker and retry mechanisms to improve the robustness
of external service interactions (e.g., OpenAI, Tavily).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Import rate limit exceptions from various providers
# These are conditionally imported to avoid hard dependencies
try:
    from litellm.exceptions import RateLimitError as LiteLLMRateLimitError
except ImportError:
    LiteLLMRateLimitError = None  # type: ignore[misc, assignment]

try:
    from openai import RateLimitError as OpenAIRateLimitError
except ImportError:
    OpenAIRateLimitError = None  # type: ignore[misc, assignment]

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# Build a tuple of rate limit exceptions that are available
def _get_rate_limit_exceptions() -> tuple[type[Exception], ...]:
    """Get all available rate limit exception types."""
    exceptions: list[type[Exception]] = []
    if LiteLLMRateLimitError is not None:
        exceptions.append(LiteLLMRateLimitError)
    if OpenAIRateLimitError is not None:
        exceptions.append(OpenAIRateLimitError)
    return tuple(exceptions) if exceptions else (Exception,)


RATE_LIMIT_EXCEPTIONS = _get_rate_limit_exceptions()


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


def create_circuit_breaker[T](
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


# Standard retry configuration for external APIs (non-LLM)
external_api_retry = create_circuit_breaker(
    max_failures=3,
    reset_timeout=30,
    exceptions=(
        TimeoutError,
        ConnectionError,
        # Add other transient errors here
    ),
)


def create_rate_limit_retry[T](
    max_attempts: int = 5,
    min_wait: float = 10.0,
    max_wait: float = 120.0,
    multiplier: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Create a retry decorator specifically for rate limit errors.

    Uses longer exponential backoff suitable for rate limits
    (e.g., Azure OpenAI free tier is 2 req/60s).

    Args:
        max_attempts: Maximum retry attempts (default: 5).
        min_wait: Minimum wait time in seconds (default: 10s).
        max_wait: Maximum wait time in seconds (default: 120s).
        multiplier: Exponential backoff multiplier (default: 2.0).

    Returns:
        A retry decorator configured for rate limit handling.
    """
    # Combine rate limit exceptions with transient errors
    all_exceptions = (*RATE_LIMIT_EXCEPTIONS, TimeoutError, ConnectionError)

    return retry(
        retry=retry_if_exception_type(all_exceptions),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        before_sleep=log_retry_attempt,
        reraise=True,
    )


# Rate limit aware retry for LLM/AI API calls
# Uses longer backoff (10-120s) to handle rate limits gracefully
llm_api_retry = create_rate_limit_retry(
    max_attempts=5,
    min_wait=10.0,
    max_wait=120.0,
    multiplier=2.0,
)


async def async_call_with_retry[T](
    fn: Callable[..., T],
    *args: object,
    attempts: int = 3,
    backoff_seconds: float = 1.0,
    handle_rate_limits: bool = True,
    **kwargs: object,
) -> T:
    """Call a sync or async function with retry logic.

    This is a shared utility for DSPy and other callable invocations that may fail
    transiently. Handles both sync and async callables uniformly.

    Args:
        fn: The function to call (sync or async).
        *args: Positional arguments to pass to the function.
        attempts: Maximum number of retry attempts (default: 3).
        backoff_seconds: Fixed wait time between retries in seconds (default: 1.0).
        handle_rate_limits: Whether to handle rate limit errors with longer backoff (default: True).
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The result of the function call.

    Raises:
        Exception: Re-raises the last exception if all retries fail.
    """
    import asyncio

    from tenacity import (
        AsyncRetrying,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
        wait_fixed,
    )

    # Ensure valid bounds
    attempts = max(1, attempts)
    backoff_seconds = max(0.0, backoff_seconds)

    # Determine which exceptions to retry on.
    #
    # This helper is intentionally broad (retries on most `Exception` types) since
    # it is used as a general "make it resilient" wrapper for both sync/async
    # callables. Callers that need narrower behavior should use the dedicated
    # decorators above (e.g. `external_api_retry`, `llm_api_retry`).
    retry_exceptions: tuple[type[Exception], ...] = (Exception,)
    if handle_rate_limits:
        # Keep explicit rate-limit types for clarity (even though they are
        # typically subclasses of `Exception`).
        retry_exceptions = (*RATE_LIMIT_EXCEPTIONS, *retry_exceptions)

    # Use exponential backoff for rate limit aware retries
    if handle_rate_limits:
        wait_strategy = wait_exponential(multiplier=2, min=backoff_seconds, max=120)
    else:
        wait_strategy = wait_fixed(backoff_seconds)

    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(attempts),
        wait=wait_strategy,
        retry=retry_if_exception_type(retry_exceptions),
        reraise=True,
        before_sleep=log_retry_attempt,
    ):
        with attempt:
            result = fn(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return result  # type: ignore[return-value]

    # This line should never be reached due to reraise=True above
    raise RuntimeError("Retry loop completed without result or exception")
