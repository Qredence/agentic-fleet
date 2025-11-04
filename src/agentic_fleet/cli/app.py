"""AgenticFleet CLI entry point."""

from __future__ import annotations

import typer

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command(name="workflow")
def workflow_command() -> None:
    """Interactive workflow CLI for testing and running workflows."""
    from agentic_fleet.cli.workflow import main as workflow_main

    workflow_main()


@app.callback(invoke_without_command=True)
def main() -> None:
    """AgenticFleet CLI entry point."""
    # Default to workflow command if no subcommand provided
    workflow_command()


if __name__ == "__main__":
    app()
