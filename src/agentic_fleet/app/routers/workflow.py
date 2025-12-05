"""Deprecated router: merged into api.py.

Kept as a thin alias for backward compatibility with legacy imports.
Existing code can continue to `from agentic_fleet.app.routers.workflow import router`.
"""

from agentic_fleet.app.routers.api import api_router as router

__all__ = ["router"]
