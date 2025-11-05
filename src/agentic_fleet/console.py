"""Enhanced CLI console with SSE streaming support."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

import typer

from agentic_fleet.api.workflow_factory import WorkflowFactory
from agentic_fleet.utils.logging import setup_logging

app = typer.Typer(add_completion=False, no_args_is_help=True)
logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

if TYPE_CHECKING:

    def command(*args: Any, **kwargs: Any) -> Callable[[F], F]: ...

    def callback(*args: Any, **kwargs: Any) -> Callable[[F], F]: ...

else:
    command = app.command
    callback = app.callback


@command()
def workflow(
    workflow_id: str = typer.Argument("magentic_fleet", help="Workflow ID to run"),
    message: str = typer.Option("", "--message", "-m", help="Message to process"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Enable SSE streaming"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Run a workflow interactively with SSE streaming support."""
    setup_logging("DEBUG" if verbose else "INFO")

    factory = WorkflowFactory()
    try:
        workflow_instance = factory.create_from_yaml(workflow_id)
        logger.info(f"Loaded workflow '{workflow_id}'")

        if not message:
            # Interactive mode
            typer.echo("Enter messages (type 'exit' to quit):")
            while True:
                try:
                    user_input = input("\n> ")
                    if user_input.lower() in ("exit", "quit"):
                        break
                    if not user_input.strip():
                        continue

                    asyncio.run(_run_workflow_message(workflow_instance, user_input, stream))
                except KeyboardInterrupt:
                    typer.echo("\nExiting...")
                    break
        else:
            # Single message mode
            asyncio.run(_run_workflow_message(workflow_instance, message, stream))

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@callback()
def _default(ctx: typer.Context) -> None:
    """Default action: start interactive workflow if no subcommand provided."""
    if ctx.invoked_subcommand is None:
        # Start interactive session with defaults
        try:
            workflow()
        except SystemExit:
            # Allow Typer to handle exit codes from nested call
            raise
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"CLI error: {e}")
            raise typer.Exit(1) from e


async def _run_workflow_message(workflow_instance: Any, message: str, stream: bool) -> None:
    """Run workflow with a message and display results.

    Args:
        workflow_instance: Workflow instance
        message: Message to process
        stream: Whether to stream events
    """
    if stream:
        typer.echo(f"[Streaming events for: {message[:50]}...]\n")
        async for event in workflow_instance.run(message):
            event_type = event.get("type", "unknown")
            event_data = event.get("data", {})

            if event_type == "message.delta":
                delta = event_data.get("delta", "")
                if delta:
                    sys.stdout.write(delta)
                    sys.stdout.flush()
            elif event_type == "message.done":
                result = event_data.get("result", "")
                if result:
                    typer.echo(f"\n\n[Done] Result: {result[:100]}...")
                else:
                    typer.echo("\n\n[Done]")
            elif event_type == "error":
                error = event_data.get("error", "Unknown error")
                typer.echo(f"\n[Error] {error}", err=True)
            elif event_type in ("progress", "orchestrator.message"):
                # Log progress events but don't display prominently
                logger.debug(f"Progress: {event_type} - {event_data}")
            else:
                logger.debug(f"Event: {event_type} - {json.dumps(event_data)[:100]}")
    else:
        # Non-streaming mode - collect all events
        typer.echo(f"[Processing: {message[:50]}...]\n")
        full_result = ""
        async for event in workflow_instance.run(message):
            event_type = event.get("type", "unknown")
            event_data = event.get("data", {})

            if event_type == "message.delta":
                delta = event_data.get("delta", "")
                full_result += delta
            elif event_type == "message.done":
                result = event_data.get("result", "")
                if result:
                    full_result += result

        typer.echo(f"\n[Result]\n{full_result}")


@command()
def list_workflows() -> None:
    """List all available workflows."""
    setup_logging()
    factory = WorkflowFactory()
    workflows = factory.list_available_workflows()

    if not workflows:
        typer.echo("No workflows found")
        return

    typer.echo("\nAvailable workflows:\n")
    for wf in workflows:
        typer.echo(f"  • {wf['id']}: {wf['name']}")
        typer.echo(f"    {wf['description']}")
        typer.echo(f"    Agents: {wf['agent_count']}\n")


if __name__ == "__main__":
    app()
