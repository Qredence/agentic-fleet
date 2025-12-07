"""CLI package for AgenticFleet command-line interface.

This package provides the command-line entry points for the AgenticFleet application.
The main entry point is `app` which is a Typer application, imported lazily to avoid
double-loading warnings when invoked via `python -m agentic_fleet.cli.console`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agentic_fleet.cli.display import display_result, show_help, show_status
from agentic_fleet.cli.runner import WorkflowRunner

if TYPE_CHECKING:  # pragma: no cover - helps IDEs without eager import
    from typer import Typer

__all__ = ["WorkflowRunner", "app", "display_result", "show_help", "show_status"]

# Satisfy type checker - actual app is loaded lazily via __getattr__
app: Typer | None = None


def __getattr__(name: str) -> Typer:
    """
    Lazily load and return the package's Typer application when accessed as an attribute.

    Parameters:
        name (str): Attribute name being accessed; only the value "app" is supported.

    Returns:
        Typer: The Typer application provided by agentic_fleet.cli.console.app.

    Raises:
        AttributeError: If `name` is not "app".
    """
    if name == "app":
        from agentic_fleet.cli import console as _console

        return _console.app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
