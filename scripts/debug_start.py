"""Deprecated debug starter.

This script previously attempted to run the backend from the old
``agentic_fleet.api`` package. The app now lives under
``agentic_fleet.app.main`` and the supported entrypoints are:

- ``make backend`` (backend only, reload)
- ``make dev`` (full stack)
- ``uv run uvicorn agentic_fleet.app.main:app --reload --port 8000``

Keeping this stub prevents accidental use of the outdated import path.
"""

raise SystemExit("scripts/debug_start.py is deprecated. Use `make backend` or `make dev` instead.")
