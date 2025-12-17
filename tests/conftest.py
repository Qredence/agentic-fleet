import logging
import os
import sys
from pathlib import Path

import pytest

# Ensure the repository root (and src dir) are importable for tests.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Ensure agent-framework shims are applied before any tests import `agent_framework`
# internals directly (some upstream distributions ship an empty root module).
from agentic_fleet.utils.agent_framework_shims import ensure_agent_framework_shims  # noqa: E402

ensure_agent_framework_shims()

# Keep DSPy disk cache inside the workspace so it remains writable in sandboxed CI.
# Consolidated under .var/cache/ following project conventions.
DSPY_CACHE = ROOT / ".var" / "cache" / "dspy"
DSPY_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DSPY_CACHEDIR", str(DSPY_CACHE))


@pytest.fixture(scope="session", autouse=True)
def suppress_litellm_cleanup_errors():
    """
    Suppress noisy LiteLLM async client cleanup errors during test teardown.

    LiteLLM registers an atexit handler to close async HTTP clients, but by the time
    it runs, pytest-asyncio has already torn down the event loop. This fixture
    suppresses the resulting RuntimeError/ValueError log spam.
    """
    yield
    # After all tests complete, suppress LiteLLM cleanup errors
    logging.getLogger("litellm").setLevel(logging.CRITICAL)
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)


@pytest.fixture(autouse=True)
def remove_cosmos_env_vars(monkeypatch):
    """
    Disable Cosmos side effects during tests.

    The cache decorator mirrors entries to Cosmos when enabled; tests should
    run with cloud integrations off to avoid network calls.
    """
    monkeypatch.delenv("AZURE_COSMOS_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_COSMOS_KEY", raising=False)


@pytest.fixture(autouse=True)
def disable_external_llm_calls(monkeypatch):
    """Make unit tests hermetic by default (no real LLM/network calls).

    Some code paths (DSPy/LiteLLM/OpenAI) may be exercised transitively during
    unit tests (e.g., NLU intent classification in DSPyReasoner). In CI we
    must never depend on external APIs, quotas, or credentials.

    To opt-in for local experimentation, set:

        AGENTIC_FLEET_TEST_ALLOW_LLM_CALLS=1
    """

    allow = os.environ.get("AGENTIC_FLEET_TEST_ALLOW_LLM_CALLS", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if allow:
        yield
        return

    # Ensure DSPy short-circuits any LLM-backed predictors.
    try:
        import dspy

        if getattr(dspy, "settings", None) is not None:
            monkeypatch.setattr(dspy.settings, "lm", None, raising=False)
    except Exception:
        # DSPy may not be importable in some minimal environments.
        pass

    # Reset our shared LM manager so nothing caches a configured LM across tests.
    try:
        from agentic_fleet.dspy_modules.lifecycle.manager import reset_dspy_manager

        reset_dspy_manager()
    except Exception:
        pass

    # Guardrail: if something still tries to call LiteLLM, fail fast with a clear error.
    try:
        import litellm

        def _blocked(*_args, **_kwargs):
            raise RuntimeError(
                "External LLM calls are disabled in unit tests. "
                "Set AGENTIC_FLEET_TEST_ALLOW_LLM_CALLS=1 to opt in."
            )

        monkeypatch.setattr(litellm, "completion", _blocked, raising=False)
        monkeypatch.setattr(litellm, "acompletion", _blocked, raising=False)
    except Exception:
        pass

    yield


@pytest.fixture
def client():
    from unittest.mock import AsyncMock, MagicMock, patch

    from fastapi.testclient import TestClient

    from agentic_fleet.main import app

    with patch(
        "agentic_fleet.api.lifespan.create_supervisor_workflow", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = MagicMock()
        with TestClient(app) as client:
            yield client
