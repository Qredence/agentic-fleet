#!/usr/bin/env python3
"""Enhanced CLI console for DSPy-Agent-Framework with SSE streaming support."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv

# Allow running as a script (python -m agentic_fleet.cli.console) by configuring package context
if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    globals()["__package__"] = "agentic_fleet.cli"

from ..utils.cfg import validate_agentic_fleet_env
from .commands import dev as dev_module
from .commands import eval as eval_module
from .commands import handoff as handoff_module
from .commands import inspect as inspect_module
from .commands import optimize, run
from .runner import WorkflowRunner  # noqa: F401

# Suppress OpenTelemetry OTLP log export errors early (before any imports trigger setup)
logging.getLogger("opentelemetry.exporter.otlp.proto.grpc.exporter").setLevel(logging.CRITICAL)
logging.getLogger("opentelemetry.sdk._logs._internal").setLevel(logging.CRITICAL)

# Load environment variables
load_dotenv()

# Validate environment variables early
try:
    validate_agentic_fleet_env()
except Exception as e:  # pragma: no cover - defensive logging
    # Log but don't fail immediately - some commands might not need API keys
    logging.getLogger(__name__).warning(f"Environment validation warning: {e}")

# Initialize Typer app
app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="DSPy-Agent-Framework CLI - Intelligent Multi-Agent Workflows",
)

app.command(name="run")(run.run)
app.command(name="dev")(dev_module.dev)

# Backward-compatible alias so tests and external callers can use
# `console.handoff` directly as a Typer command function rather than
# importing the submodule.
handoff = handoff_module.handoff
app.command(name="handoff")(handoff)
app.command(name="analyze")(inspect_module.analyze)
app.command(name="benchmark")(eval_module.benchmark)
app.command(name="list-agents")(inspect_module.list_agents)
app.command(name="export-history")(inspect_module.export_history)
app.command(name="gepa-optimize")(optimize.gepa_optimize)
app.command(name="self-improve")(inspect_module.self_improve)
app.command(name="evaluate")(eval_module.evaluate)


if __name__ == "__main__":
    app()
