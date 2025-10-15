"""Interactive REPL for AgenticFleet with rich console feedback."""

import asyncio
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from rich.table import Table
from rich.text import Text

from agenticfleet.cli.ui import ConsoleUI
from agenticfleet.config import settings
from agenticfleet.core.logging import get_logger

if TYPE_CHECKING:
    from agenticfleet.fleet.magentic_fleet import MagenticFleet

logger = get_logger(__name__)

_workflow_instance = None


def get_workflow(ui: ConsoleUI | None = None) -> "MagenticFleet":
    """
    Get the Magentic Fleet workflow instance, creating it on first use.
    """
    global _workflow_instance

    if _workflow_instance is None:
        logger.info("Using Magentic Fleet workflow")
        from agenticfleet.fleet import create_default_fleet

        _workflow_instance = create_default_fleet(console_ui=ui)
    elif ui is not None:  # type: ignore[unreachable]
        _workflow_instance.console_callbacks.bind_ui(ui)

    return _workflow_instance


async def handle_checkpoint_command(
    command: str, workflow_instance: "MagenticFleet", ui: ConsoleUI
) -> bool:
    """
    Handle checkpoint-related commands.

    Args:
        command: The command string to handle
        workflow_instance: The workflow instance to use

    Returns:
        True if command was handled, False otherwise
    """
    parts = command.split()

    if parts[0] == "checkpoints" or parts[0] == "list-checkpoints":
        if not hasattr(workflow_instance, "list_checkpoints"):
            ui.log_notice("Checkpoint listing is not available for this workflow.", style="red")
            return True

        checkpoints = await workflow_instance.list_checkpoints()
        if not checkpoints:
            ui.log_notice("No checkpoints found.", style="yellow")
        else:
            table = Table(title=f"Available Checkpoints ({len(checkpoints)})", expand=True)
            table.add_column("Checkpoint ID", style="cyan")
            table.add_column("Workflow ID", style="magenta")
            table.add_column("Round", justify="center")
            table.add_column("Timestamp", style="green")
            table.add_column("Status", style="yellow")
            for cp in checkpoints:
                timestamp = cp.get("timestamp", "unknown")
                # Format timestamp if it's an ISO string
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # If timestamp is not valid ISO format, use as-is
                    pass

                metadata = cp.get("metadata", {})
                status = metadata.get("status", "unknown") if metadata else "—"
                table.add_row(
                    cp.get("checkpoint_id", "—"),
                    cp.get("workflow_id", "—"),
                    str(cp.get("current_round", "—")),
                    timestamp,
                    status,
                )

            ui.console.print(table)
        return True

    elif parts[0] == "resume" and len(parts) > 1:
        # Resume from checkpoint
        checkpoint_id = parts[1]
        ui.log_notice(f"Attempting to resume from checkpoint: {checkpoint_id}", style="cyan")

        if not hasattr(workflow_instance, "run"):
            ui.log_notice("Current workflow cannot resume from checkpoints.", style="red")
            return True

        ui._print_section("Continue task", [], pre_blank=True)
        user_input = await ui.prompt_async("Continue task")
        if not user_input:
            ui.log_notice("No input provided. Resuming cancelled.", style="yellow")
            return True

        ui.console.rule(style="cyan")

        try:
            result = await workflow_instance.run(user_input, resume_from_checkpoint=checkpoint_id)

            ui.log_notice("Task completed from checkpoint", style="green")
            ui.log_final(result or "")

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            ui.log_notice(f"Error resuming workflow: {e}", style="red")

        return True

    return False


async def run_repl(workflow_instance: "MagenticFleet", ui: ConsoleUI) -> None:
    """
    Run the interactive REPL loop for user interaction.

    Args:
        workflow_instance: The workflow instance to use for task execution
    """
    while True:
        try:
            user_input = await ui.prompt_async()

            if user_input.lower() in ["quit", "exit", "q"]:
                ui.log_notice("Thank you for using AgenticFleet!", style="green")
                break

            if not user_input:
                continue

            # Handle checkpoint commands
            if user_input.startswith(("checkpoints", "list-checkpoints", "resume")):
                handled = await handle_checkpoint_command(user_input, workflow_instance, ui)
                if handled:
                    continue

            safe_user_input = user_input.replace("\r", "").replace("\n", "")
            logger.info(f"Processing: '{safe_user_input}'")
            ui.console.print(Text("=" * 72, style="dim"))
            ui.reset_run()
            ui.log_task(user_input)

            try:
                ui.log_notice("Working with Magentic planner…")
                with ui.loading("Coordinating Magentic Fleet..."):
                    result = await workflow_instance.run(user_input)

                final_render = workflow_instance.console_callbacks.consume_final_render()
                if final_render is None:
                    ui.log_final(result or "")
                ui.console.print(Text("Ready for next task", style="bold"))
                ui.console.print(Text("=" * 72, style="dim"))

            except Exception as e:
                logger.error(f"Workflow execution failed: {e}", exc_info=True)
                logger.error(
                    "This might be due to API rate limits, complex tasks, "
                    "or agent coordination failures."
                )
                logger.error("Try simplifying your request or checking your API key and quota.")
                ui.log_notice("Workflow execution failed. Check logs for details.")

            ui.console.print(Text("=" * 72, style="dim"))
            ui.console.print(Text("Ready for next task", style="bold"))

        except KeyboardInterrupt:
            logger.warning("Session interrupted by user")
            confirm = (await ui.prompt_async("Exit? (y/n)")).lower()
            if confirm in ["y", "yes"]:
                logger.info("Goodbye!")
                break
            else:
                logger.info("Continuing...")
                continue


def run_repl_main() -> int:
    """
    Main entry point for the REPL interface.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("Starting AgenticFleet - Phase 1")
    logger.info("Powered by Microsoft Agent Framework")
    logger.info("Using OpenAI with structured responses")

    ui = ConsoleUI()

    ui.show_header()
    ui.show_instructions()

    try:
        if not settings.openai_api_key:
            ui.log_notice("OPENAI_API_KEY environment variable is required", style="red")
            ui.log_notice(
                "Please copy .env.example to .env and add your OpenAI API key", style="yellow"
            )
            return 1
    except Exception as e:
        logger.error(f"Configuration Error: {e}", exc_info=True)
        ui.log_notice(f"Configuration error: {e}", style="red")
        return 1

    workflow_instance = get_workflow(ui)
    ui.log_notice("Magentic workflow ready")

    checkpoint_config = settings.workflow_config.get("workflow", {}).get("checkpointing", {})
    if checkpoint_config.get("enabled", False):
        storage_path = checkpoint_config.get("storage_path", "./checkpoints")
        ui.log_notice(f"Checkpointing enabled (storage: {storage_path})")
    else:
        ui.log_notice("Checkpointing disabled")

    hitl_config = settings.workflow_config.get("workflow", {}).get("human_in_the_loop", {})
    if hitl_config.get("enabled", False):
        timeout = hitl_config.get("approval_timeout_seconds", 300)
        operations = ", ".join(hitl_config.get("require_approval_for", [])) or "(none)"
        ui.log_notice(f"HITL enabled (timeout: {timeout}s) – approvals: {operations}")
    else:
        ui.log_notice("Human-in-the-Loop disabled")

    try:
        asyncio.run(run_repl(workflow_instance, ui))
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        ui.log_notice(f"Fatal error: {e}", style="red")
        return 1
    finally:
        workflow_instance.console_callbacks.bind_ui(None)


def main() -> None:
    """
    Console script entry point.

    This is called when running: uv run agentic-fleet

    Accepts an optional --workflow flag for backwards compatibility; all values
    resolve to the Magentic implementation.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="AgenticFleet - Multi-agent AI system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--workflow",
        default="magentic",
        help="Workflow mode to use (legacy option is deprecated)",
    )

    args = parser.parse_args()

    if args.workflow != "magentic":
        logger.warning(
            "Legacy workflow mode '%s' is no longer available; falling back to Magentic.",
            args.workflow,
        )

    sys.exit(run_repl_main())


if __name__ == "__main__":
    main()
