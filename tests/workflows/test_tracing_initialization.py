"""Workflow tracing wiring tests.

These tests ensure that workflow initialization uses the YAML configuration
(including the `tracing:` section) when initializing OpenTelemetry.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_initialize_workflow_context_uses_yaml_tracing_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Workflow initialization should initialize tracing from loaded YAML config.

    We stop execution immediately after tracing setup to keep the test fast and
    avoid network/API dependencies.
    """

    from agentic_fleet.workflows import initialization as init_mod

    sentinel_cfg = {
        "tracing": {"enabled": True, "otlp_endpoint": "http://example:4317"},
        "agents": {},
    }

    # Patch the YAML config loader (imported into the initialization module)
    # to return a deterministic tracing config.
    monkeypatch.setattr(init_mod, "load_config", lambda *args, **kwargs: sentinel_cfg)

    observed: dict[str, object] = {}

    def fake_initialize_tracing(cfg):
        observed["cfg"] = cfg
        return True

    monkeypatch.setattr(init_mod, "initialize_tracing", fake_initialize_tracing)

    # Avoid environment validation and Agent Framework shim side-effects.
    monkeypatch.setattr(init_mod, "_validate_environment", lambda: None)
    monkeypatch.setattr(init_mod, "ensure_agent_framework_shims", lambda: None)

    # Stop right after tracing initialization.
    def stop_create_shared_components(*args, **kwargs):
        raise RuntimeError("stop-after-tracing")

    monkeypatch.setattr(init_mod, "_create_shared_components", stop_create_shared_components)

    with pytest.raises(RuntimeError, match="stop-after-tracing"):
        await init_mod.initialize_workflow_context()

    assert observed["cfg"] == sentinel_cfg
