"""Application entry point for AgenticFleet."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

from agentic_fleet.api.app import app

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore[assignment]

try:
    from agent_framework.observability import setup_observability
except ImportError:  # pragma: no cover - optional dependency
    setup_observability = None  # type: ignore[assignment]


def _optional_call(func: Callable[..., Any] | None) -> None:
    if func is not None:
        func()


# Load environment as early as possible to support uvicorn workers.
_optional_call(load_dotenv)
_optional_call(setup_observability)


def main() -> None:
    """Run the FastAPI application using uvicorn."""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger = logging.getLogger("agentic_fleet.main")

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("UVICORN_LOG_LEVEL", "info")
    reload = os.getenv("ENVIRONMENT", "development") != "production"

    logger.info("Starting AgenticFleet API...")
    logger.info("HTTP server listening on http://%s:%d", host, port)

    uvicorn.run(
        "agentic_fleet.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        factory=False,
    )


__all__ = ["app", "main"]


if __name__ == "__main__":
    main()
