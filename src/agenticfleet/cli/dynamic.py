"""CLI entry point for dynamic workflow runner.

This lightweight script starts the FastAPI server but sets an environment
flag so the application can behave in "dynamic" workflow mode if it
checks the environment variable. It avoids importing non-existent symbols
so importing this module remains cheap.
"""

from __future__ import annotations

import os

import uvicorn

from agenticfleet.server import app


def main() -> None:
    """Run AgenticFleet server in dynamic workflow mode.

    Sets WORKFLOW_MODE=dynamic in the environment before starting Uvicorn so
    the application can detect the intent when it initializes.
    """
    os.environ.setdefault("WORKFLOW_MODE", "dynamic")
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)


if __name__ == "__main__":
    main()
