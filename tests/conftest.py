import os
import sys
from pathlib import Path

import pytest

# Ensure the repository root (and src dir) are importable for tests.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Keep DSPy disk cache inside the workspace so it remains writable in sandboxed CI.
DSPY_CACHE = ROOT / ".cache" / "dspy"
DSPY_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DSPY_CACHEDIR", str(DSPY_CACHE))


@pytest.fixture(autouse=True)
def disable_cosmos(monkeypatch):
    """
    Disable Cosmos side effects during tests.

    The cache decorator mirrors entries to Cosmos when enabled; tests should
    run with cloud integrations off to avoid network calls.
    """
    monkeypatch.delenv("AZURE_COSMOS_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_COSMOS_KEY", raising=False)

    # Force disable Cosmos DB usage in settings
    # from agentic_fleet.api.settings import settings
    # monkeypatch.setattr(settings, "AGENTICFLEET_USE_COSMOS", False)
    return


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from agentic_fleet.app.main import app

    with TestClient(app) as client:
        yield client
