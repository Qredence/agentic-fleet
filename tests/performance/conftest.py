"""Autostart Uvicorn server for performance tests.

This ensures tests/performance/test_sse_performance.py can connect to
http://localhost:8000 without manual server startup. Runs once per test
session when PYTEST is active.
"""

from __future__ import annotations

import os
import threading
import time

import httpx
import pytest
import uvicorn

from agentic_fleet.api.app import create_app

_server_started = False


@pytest.fixture(scope="session", autouse=True)
def start_uvicorn_server() -> None:  # pragma: no cover - infrastructure
    global _server_started
    if _server_started:
        return
    # Only start during pytest runs, guard to avoid side-effects in prod
    if "PYTEST_CURRENT_TEST" not in os.environ:
        return
    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="error")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for health endpoint to come up
    for _ in range(50):  # ~5s max
        try:
            r = httpx.get("http://127.0.0.1:8000/v1/system/health", timeout=0.2)
            if r.status_code == 200:
                _server_started = True
                break
        except Exception:
            pass
        time.sleep(0.1)
