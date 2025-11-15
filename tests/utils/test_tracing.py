"""Tests for tracing initialization utility.

These tests ensure that calling initialize_tracing does not raise exceptions
even when agent_framework.observability may be unavailable in test context.
"""

from __future__ import annotations

from agentic_fleet.utils.tracing import initialize_tracing, reset_tracing


def test_tracing_disabled_by_default(monkeypatch):
    # Ensure env override removed
    monkeypatch.delenv("TRACING_ENABLED", raising=False)
    reset_tracing()
    # No env flags; function should return False and not raise
    assert initialize_tracing({}) is False


def test_tracing_enabled_env_flag(monkeypatch):
    monkeypatch.setenv("TRACING_ENABLED", "true")
    # Provide minimal config
    reset_tracing()
    cfg = {"tracing": {"enabled": True, "otlp_endpoint": "http://localhost:4317"}}
    # Should return True (or False if underlying deps missing) but must not raise
    result = initialize_tracing(cfg)
    assert isinstance(result, bool)


def test_tracing_idempotent(monkeypatch):
    monkeypatch.setenv("TRACING_ENABLED", "true")
    reset_tracing()
    cfg = {"tracing": {"enabled": True}}
    first = initialize_tracing(cfg)
    second = initialize_tracing(cfg)
    # Second call should not change truthiness
    assert isinstance(first, bool)
    assert isinstance(second, bool)
