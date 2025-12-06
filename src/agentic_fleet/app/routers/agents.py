"""Deprecated router: merged into api.py.

Kept as a thin alias for backward compatibility with legacy imports.
"""

from agentic_fleet.app.routers.api import api_router as router

__all__ = ["router"]
