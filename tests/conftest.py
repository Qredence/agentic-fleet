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


@pytest.fixture(autouse=True)
def remove_cosmos_env_vars(monkeypatch):
    """
    Disable Cosmos side effects during tests.

    The cache decorator mirrors entries to Cosmos when enabled; tests should
    run with cloud integrations off to avoid network calls.
    """
    monkeypatch.delenv("AZURE_COSMOS_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_COSMOS_KEY", raising=False)


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
