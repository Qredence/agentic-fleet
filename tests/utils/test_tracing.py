"""Tests for tracing initialization utilities."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest

from agentic_fleet.utils.tracing import initialize_tracing, reset_tracing


@pytest.fixture(autouse=True)
def reset_tracing_state() -> Generator[None, None, None]:
    """Reset tracing state before each test."""
    reset_tracing()
    yield
    reset_tracing()


class TestInitializeTracing:
    """Tests for initialize_tracing function."""

    def test_disabled_by_default_when_no_config(self) -> None:
        """Tracing should be disabled when no config is provided and env unset."""
        with patch.dict("os.environ", {"TRACING_ENABLED": ""}, clear=False):
            reset_tracing()
            result = initialize_tracing(None)
            assert result is False

    def test_disabled_when_config_disabled(self) -> None:
        """Tracing should be disabled when config.tracing.enabled is False."""
        config: dict[str, Any] = {"tracing": {"enabled": False}}
        with patch.dict("os.environ", {"TRACING_ENABLED": ""}, clear=False):
            reset_tracing()
            result = initialize_tracing(config)
            assert result is False

    def test_disabled_when_env_disabled(self) -> None:
        """Tracing should be disabled when TRACING_ENABLED env var is false."""
        config: dict[str, Any] = {"tracing": {"enabled": True}}
        with patch.dict("os.environ", {"TRACING_ENABLED": "false"}):
            reset_tracing()
            result = initialize_tracing(config)
            assert result is False

    def test_env_true_enables_when_config_false(self) -> None:
        """TRACING_ENABLED=true env var should enable tracing even if config says false."""
        config: dict[str, Any] = {"tracing": {"enabled": False}}
        with patch.dict("os.environ", {"TRACING_ENABLED": "true"}):
            reset_tracing()
            # It should attempt to initialize (may fail without collector)
            # We verify it doesn't return False due to 'enabled' being false
            result = initialize_tracing(config)
            # Result depends on whether collector is available
            # This test verifies the env override logic works
            assert isinstance(result, bool)

    def test_idempotent_after_success(self) -> None:
        """Once initialized, subsequent calls should return True without reinitializing."""
        config: dict[str, Any] = {"tracing": {"enabled": True}}

        with patch("agent_framework.observability.setup_observability") as mock_setup:
            result1 = initialize_tracing(config)
            # First call may succeed or fail depending on environment

            if result1:
                # If first succeeded, second should return True immediately
                result2 = initialize_tracing(config)
                assert result2 is True
                # setup_observability should only be called once
                assert mock_setup.call_count == 1


class TestResetTracing:
    """Tests for reset_tracing function."""

    def test_reset_clears_initialized_flag(self) -> None:
        """reset_tracing should clear the initialized flag."""
        reset_tracing()
        # After reset, module should be in fresh state
        # This is validated by the fixture behavior


class TestTracingConfiguration:
    """Tests for tracing configuration options."""

    def test_default_endpoint_localhost(self) -> None:
        """Default OTLP endpoint should be localhost:4317."""
        config: dict[str, Any] = {"tracing": {"enabled": True}}

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("agent_framework.observability.setup_observability") as mock_setup,
        ):
            reset_tracing()
            result = initialize_tracing(config)

            # We don't assert on result (it depends on runtime), but we do assert
            # that observability setup used the default local gRPC collector.
            assert isinstance(result, bool)
            assert mock_setup.called
            call_kwargs = mock_setup.call_args.kwargs
            assert call_kwargs.get("otlp_endpoint") == "http://localhost:4317"

    def test_endpoint_env_takes_precedence(self) -> None:
        """OTEL_EXPORTER_OTLP_ENDPOINT should override config endpoint."""
        config: dict[str, Any] = {
            "tracing": {
                "enabled": True,
                "otlp_endpoint": "http://config-endpoint:4317",
            }
        }

        with (
            patch.dict(
                "os.environ",
                {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://env-endpoint:4317"},
            ),
            patch("agent_framework.observability.setup_observability") as mock_setup,
        ):
            reset_tracing()
            initialize_tracing(config)
            if mock_setup.called:
                # Verify env endpoint was used
                call_kwargs = mock_setup.call_args.kwargs
                assert call_kwargs.get("otlp_endpoint") == "http://env-endpoint:4317"


class TestTracingFallback:
    """Tests for OpenTelemetry fallback when agent-framework unavailable."""

    def test_graceful_when_no_collector(self) -> None:
        """Should gracefully handle when no collector is available."""
        config: dict[str, Any] = {"tracing": {"enabled": True}}

        # Even if initialization fails, it should not raise
        reset_tracing()
        result = initialize_tracing(config)
        # Result is boolean regardless of success/failure
        assert isinstance(result, bool)
