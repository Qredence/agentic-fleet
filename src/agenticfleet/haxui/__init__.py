"""AgenticFleet HaxUI backend package.

Exposes a FastAPI application that powers the shadcn-based HaxUI frontend.
"""

from .api import create_app

__all__ = ["create_app"]
