"""CLI package for AgenticFleet command-line interface.

This package provides the command-line entry points for the AgenticFleet application.
The main entry point is `app` which is a Typer application.
"""

from __future__ import annotations

from agentic_fleet.cli.console import app
from agentic_fleet.cli.display import display_result, show_help, show_status
from agentic_fleet.cli.runner import WorkflowRunner

__all__ = ["WorkflowRunner", "app", "display_result", "show_help", "show_status"]
