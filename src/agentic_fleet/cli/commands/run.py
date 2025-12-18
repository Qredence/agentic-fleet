"""Run command for executing workflows."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from ...utils.error_utils import sanitize_error_message
from ...utils.logger import setup_logger
from ..display import display_result, show_help, show_status
from ..runner import WorkflowRunner
from ..utils import init_tracing

load_dotenv(dotenv_path=".env")  # Load .env file if present
console = Console()
logger = logging.getLogger(__name__)


async def interactive_loop(runner: WorkflowRunner, stream: bool) -> None:
    """Run interactive message loop."""
    console.print("\n[dim]Ready for input. Type 'help' for commands.[/dim]\n")

    while True:
        try:
            # Get user input
            user_input = console.input("[bold blue]You>[/bold blue] ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ("exit", "quit"):
                console.print("[yellow]Goodbye![/yellow]")
                break
            elif user_input.lower() == "clear":
                console.clear()
                continue
            elif user_input.lower() == "help":
                show_help(console)
                continue
            elif user_input.lower() == "status":
                show_status(runner, console)
                continue

            # Process as task
            console.print()
            if stream:
                await runner.run_with_streaming(user_input)
            else:
                result = await runner.run_without_streaming(user_input)
                display_result(result)
            console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit[/yellow]\n")
        except EOFError:
            # Non-interactive stdin (or closed input) should not spin forever.
            console.print("\n[yellow]EOF received. Exiting interactive mode.[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]\n")


def run(
    # Accept message via option or positional argument for convenience
    message: str | None = typer.Option(
        None,
        "--message",
        "-m",
        help="Message to process (you can also pass it positionally)",
    ),
    task: str | None = typer.Argument(None, help="Message to process (positional)"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Enable streaming output"),
    compile_dspy: bool = typer.Option(True, "--compile/--no-compile", help="Compile DSPy module"),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Model to use (gpt-4.1, gpt-5-mini, gpt-5). Defaults to config.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    interactive: bool = typer.Option(True, "--interactive", "-i", help="Interactive mode"),
    handoffs: bool | None = typer.Option(
        None,
        "--handoffs/--no-handoffs",
        help="Force enable/disable structured handoffs (defaults to config)",
    ),
    fast: bool = typer.Option(
        False,
        "--fast",
        help="Optimize for latency (lighter judge/refinement settings where supported)",
    ),
    mode: str = typer.Option(
        "auto",
        "--mode",
        help="Workflow mode (auto, standard, group_chat, concurrent, handoff)",
    ),
) -> None:
    """
    Run the DSPy-enhanced workflow with a message.

    Examples:
        agentic-fleet run "Analyze renewable energy trends"
        agentic-fleet run -m "Write a blog post" --no-stream
        agentic-fleet run --model gpt-5-mini "Compare AWS vs Azure AI"
    """
    # Setup logging
    setup_logger("dspy_agent_framework", "DEBUG" if verbose else "INFO")

    # Tracing (optional) - call early so agent creation is instrumented
    init_tracing()

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]Error: OPENAI_API_KEY not found in environment[/bold red]")
        console.print("Please set it in .env file or export it")
        raise typer.Exit(1)

    runner = WorkflowRunner(verbose=verbose)

    # Pick message from option or positional argument (option takes precedence)
    message_input = message or task or ""

    async def process_message(msg: str) -> None:
        """Process a single message."""
        if stream:
            await runner.run_with_streaming(msg)
        else:
            result = await runner.run_without_streaming(msg)
            display_result(result)

    # Initialize workflow with model parameter
    async def init_runner() -> None:
        final_mode = mode

        # Handle Auto Mode
        if mode == "auto" and message_input:
            console.print("[dim]Auto-detecting workflow mode...[/dim]")
            try:
                # Quick DSPy init for decision
                import dspy

                from ...dspy_modules.lifecycle import configure_dspy_settings
                from ...dspy_modules.reasoner import DSPyReasoner

                if not dspy.settings.lm:
                    # Use dspy_manager for proper Azure OpenAI support
                    configure_dspy_settings(model or "gpt-5-mini")

                reasoner = DSPyReasoner(use_enhanced_signatures=True)
                decision = reasoner.select_workflow_mode(message_input)
                detected = decision.get("mode", "standard")

                if detected == "fast_path":
                    # Fast path can be handled by standard mode's fast-path logic,
                    # or we can run it here. Let's map it to 'standard' but let supervisor handle fast path.
                    # Actually supervisor has fast path check.
                    final_mode = "standard"
                    console.print(
                        "[bold green]Auto-detected:[/bold green] Fast Path (via Standard)"
                    )
                else:
                    final_mode = detected
                    console.print(f"[bold green]Auto-detected:[/bold green] {final_mode}")
                    console.print(f"[dim]Reasoning: {decision.get('reasoning')}[/dim]")

            except Exception as e:
                logger.warning(f"Auto-detection failed: {e}. Defaulting to standard.")
                final_mode = "standard"

        await runner.initialize_workflow(
            compile_dspy=compile_dspy,
            model=model,
            max_rounds=15,
            enable_handoffs=handoffs,
            # In fast mode, request the light pipeline profile to reduce
            # the number of LM calls for simple queries.
            pipeline_profile="light" if fast else None,
            mode=final_mode,
            allow_gepa=False,  # Disable GEPA optimization during run
        )
        # Apply optional fast-mode tuning on top of the loaded config.
        if fast and runner.workflow_config is not None:
            cfg = runner.workflow_config
            # Switch to light profile and reduce judge/refinement cost in fast mode.
            cfg.pipeline_profile = "light"
            cfg.enable_progress_eval = False
            cfg.enable_quality_eval = False
            cfg.enable_judge = False
            cfg.enable_refinement = False
            cfg.max_refinement_rounds = min(cfg.max_refinement_rounds, 1)
            cfg.judge_reasoning_effort = "minimal"

    try:
        # Interactive mode requires a TTY; otherwise Click/Typer can block forever waiting for input.
        interactive_enabled = bool(interactive and sys.stdin.isatty() and sys.stdout.isatty())
        if interactive and not interactive_enabled and not message_input:
            console.print(
                "[yellow]Interactive mode disabled (no TTY detected). "
                "Provide a message via -m/--message or pass --no-interactive.[/yellow]"
            )

        if message_input:
            # Single message mode
            asyncio.run(init_runner())
            asyncio.run(process_message(message_input))
        elif interactive_enabled:
            # Interactive mode
            console.print(
                Panel(
                    "[bold green]DSPy-Agent-Framework Interactive Console[/bold green]\n"
                    "Type your messages below. Commands:\n"
                    "  • 'exit' or 'quit' - Exit the console\n"
                    "  • 'clear' - Clear the screen\n"
                    "  • 'help' - Show this help\n"
                    "  • 'status' - Show workflow status",
                    title="Welcome",
                    border_style="green",
                )
            )

            asyncio.run(init_runner())
            asyncio.run(interactive_loop(runner, stream))
        else:
            console.print("[yellow]No message provided and interactive mode disabled[/yellow]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        sanitized_msg = sanitize_error_message(e)
        console.print(f"[bold red]Error: {sanitized_msg}[/bold red]")
        if verbose:
            logger.exception("Workflow error")
        raise typer.Exit(1) from e
