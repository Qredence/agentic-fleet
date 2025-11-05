"""AgenticFleet CLI entrypoint.

This re-exports the Rich/interactive console commands defined in
`agentic_fleet.console` so that `uv run agentic-fleet` and `uv run fleet`
provide an interactive experience out of the box.
"""

from __future__ import annotations

from agentic_fleet.console import app  # Typer app with interactive commands

if __name__ == "__main__":  # pragma: no cover
    app()
