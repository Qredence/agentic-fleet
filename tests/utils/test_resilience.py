"""Tests for resilience utilities (retry logic, circuit breaker)."""

from __future__ import annotations

import pytest

from agentic_fleet.utils.resilience import (
    async_call_with_retry,
    create_circuit_breaker,
    log_retry_attempt,
)


class TestLogRetryAttempt:
    """Tests for log_retry_attempt callback."""

    def test_logs_warning_on_failed_attempt(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify warning is logged when retry state indicates failure."""

        # Create a minimal mock retry state
        class MockOutcome:
            failed = True

            def exception(self) -> Exception:
                """
                Return a ValueError instance representing a test error.

                Returns:
                    Exception: A `ValueError` instance with the message "test error".
                """
                return ValueError("test error")

        class MockRetryState:
            outcome = MockOutcome()
            attempt_number = 2
            fn = lambda: None  # noqa: E731
            fn.__name__ = "test_function"

        with caplog.at_level("WARNING"):
            log_retry_attempt(MockRetryState())  # type: ignore[arg-type]

        assert "Retrying test_function" in caplog.text
        assert "ValueError" in caplog.text
        assert "Attempt 2" in caplog.text

    def test_handles_missing_function_name(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Log a warning using an "unknown_function" placeholder when the retry state has no function name.

        """

        class MockOutcome:
            failed = True

            def exception(self) -> Exception:
                """
                Return a RuntimeError indicating the function name is missing.

                Returns:
                    Exception: A RuntimeError with the message "no name fn".
                """
                return RuntimeError("no name fn")

        class MockRetryState:
            outcome = MockOutcome()
            attempt_number = 1
            fn = None

        with caplog.at_level("WARNING"):
            log_retry_attempt(MockRetryState())  # type: ignore[arg-type]

        assert "unknown_function" in caplog.text

    def test_no_log_on_success(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify no logging when outcome is not failed."""

        class MockOutcome:
            failed = False

        class MockRetryState:
            outcome = MockOutcome()
            attempt_number = 1
            fn = None

        with caplog.at_level("WARNING"):
            log_retry_attempt(MockRetryState())  # type: ignore[arg-type]

        assert caplog.text == ""


class TestCreateCircuitBreaker:
    """Tests for create_circuit_breaker decorator factory."""

    def test_creates_retry_decorator(self):
        """Verify decorator is created and can wrap functions."""

        @create_circuit_breaker(max_failures=2, reset_timeout=5)
        def sample_function():
            return "success"

        result = sample_function()
        assert result == "success"

    def test_retries_on_specified_exceptions(self):
        """Verify retries occur for specified exception types."""
        call_count = 0

        @create_circuit_breaker(
            max_failures=3,
            reset_timeout=1,
            exceptions=(ValueError,),
        )
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("transient error")
            return "eventually succeeded"

        result = flaky_function()
        assert result == "eventually succeeded"
        assert call_count == 2

    def test_fails_after_max_attempts(self):
        """Verify exception is raised after max_failures attempts."""
        call_count = 0

        @create_circuit_breaker(
            max_failures=2,
            reset_timeout=1,
            exceptions=(RuntimeError,),
        )
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("persistent failure")

        with pytest.raises(RuntimeError, match="persistent failure"):
            always_fails()

        assert call_count == 2

    def test_does_not_retry_unspecified_exceptions(self):
        """Verify non-matching exceptions are not retried."""
        call_count = 0

        @create_circuit_breaker(
            max_failures=3,
            reset_timeout=1,
            exceptions=(ValueError,),  # Only retry ValueError
        )
        def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")

        with pytest.raises(TypeError, match="wrong type"):
            raises_type_error()

        # Should only be called once (no retry for TypeError)
        assert call_count == 1


class TestAsyncCallWithRetry:
    """Tests for async_call_with_retry function."""

    @pytest.mark.asyncio
    async def test_calls_sync_function_successfully(self):
        """Verify sync functions are called and return correctly."""

        def sync_add(a, b):
            return a + b

        result = await async_call_with_retry(sync_add, 2, 3)
        assert result == 5

    @pytest.mark.asyncio
    async def test_calls_async_function_successfully(self):
        """Verify async functions are awaited correctly."""

        async def async_multiply(a, b):
            return a * b

        result = await async_call_with_retry(async_multiply, 4, 5)
        assert result == 20

    @pytest.mark.asyncio
    async def test_retries_sync_function_on_failure(self):
        """Verify sync functions are retried on transient failures."""
        call_count = 0

        def flaky_sync():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("transient")
            return "ok"

        result = await async_call_with_retry(flaky_sync, attempts=3, backoff_seconds=0.01)
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_async_function_on_failure(self):
        """Verify async functions are retried on transient failures."""
        call_count = 0

        async def flaky_async():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("retry me")
            return "success"

        result = await async_call_with_retry(flaky_async, attempts=5, backoff_seconds=0.01)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts_exhausted(self):
        """Verify exception is raised when all retries fail."""
        call_count = 0

        def always_fails():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("permanent failure")

        with pytest.raises(RuntimeError, match="permanent failure"):
            await async_call_with_retry(always_fails, attempts=2, backoff_seconds=0.01)

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_passes_kwargs_correctly(self):
        """Verify keyword arguments are passed to the function."""

        def kwargs_fn(*, name, value):
            return f"{name}={value}"

        result = await async_call_with_retry(kwargs_fn, name="test", value=42)
        assert result == "test=42"

    @pytest.mark.asyncio
    async def test_minimum_attempts_is_one(self):
        """Verify attempts is clamped to minimum of 1."""
        call_count = 0

        def increment():
            nonlocal call_count
            call_count += 1
            return call_count

        result = await async_call_with_retry(increment, attempts=0, backoff_seconds=0)
        assert result == 1
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_negative_backoff_is_clamped_to_zero(self):
        """Verify negative backoff is clamped to 0."""

        def simple():
            return "done"

        # Should not raise, just clamp to 0
        result = await async_call_with_retry(simple, attempts=1, backoff_seconds=-5.0)
        assert result == "done"
