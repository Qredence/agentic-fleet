"""Deprecated: synchronous starter for old agentic_fleet.api app.

The application now lives at ``agentic_fleet.app.main:app``. Please use the
standard entrypoints instead of this legacy script:

- ``make backend``
- ``make dev``
- ``uv run uvicorn agentic_fleet.app.main:app --reload --port 8000``
"""

raise SystemExit(
    "scripts/start_server_sync.py is deprecated. Use `make backend` or `make dev` instead."
)
