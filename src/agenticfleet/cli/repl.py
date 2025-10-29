"""Main CLI entry point for AgenticFleet REPL/CLI.

This module provides a simple entry point used by project scripts to start
the FastAPI/uvicorn server in development or production-like runs.
"""

from __future__ import annotations

import uvicorn

from agenticfleet.server import app


def main() -> None:
    """Run AgenticFleet server.

    This entrypoint is intentionally small — the project uses Uvicorn to run
    the FastAPI `app` exported from `agenticfleet.server`.
    """
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
