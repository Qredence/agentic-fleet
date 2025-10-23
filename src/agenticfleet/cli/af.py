"""Lightweight CLI to run the modular Magentic workflow once (non-interactive).

Usage:
    uv run python -m agenticfleet.cli.af run "Build a Python web scraper"

If packaged, this can also be exposed as a console script called `af`.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from agenticfleet.cli.ui import ConsoleUI
from agenticfleet.core.logging import get_logger
from agenticfleet.fleet.callbacks import ConsoleCallbacks
from agenticfleet.workflows._experimental_dynamic.factory import create_dynamic_workflow

logger = get_logger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="af",
        description="AgenticFleet modular Magentic runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Execute a one-off task with dynamic Magentic orchestration",
    )
    run_parser.add_argument(
        "task",
        help="Task to execute. Wrap in quotes for multi-word prompts.",
    )
    run_parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Disable optional tool agents (web search, python coder, etc.)",
    )
    run_parser.add_argument(
        "--manager-model",
        dest="manager_model",
        help="Override manager LLM model identifier",
    )
    run_parser.add_argument(
        "--manager-instructions",
        dest="manager_instructions",
        help="Override manager system prompt",
    )
    run_parser.add_argument(
        "--progress-ledger-retries",
        dest="progress_ledger_retry_count",
        type=int,
        help="Number of retries when parsing the progress ledger JSON",
    )

    return parser.parse_args(argv)


async def _run_once_async(args: argparse.Namespace) -> int:
    ui = ConsoleUI()
    ui.show_header()

    include_tools = not args.no_tools
    callbacks = ConsoleCallbacks(ui)

    workflow = create_dynamic_workflow(
        include_default_tool_agents=include_tools,
        manager_instructions=args.manager_instructions,
        manager_model=args.manager_model,
        progress_ledger_retry_count=args.progress_ledger_retry_count,
        console_callbacks=callbacks,
        streaming_enabled=True,
        log_progress=True,
    )

    ui.log_task(args.task)
    try:
        result: Any = await workflow.run(args.task)
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        logger.error("Workflow execution failed", exc_info=True)
        ui.log_notice(f"Workflow execution failed: {exc}", style="red")
        return 1

    # Render final result if callbacks did not already output a rich view
    final_render = callbacks.consume_final_render()
    if final_render is None:
        # Best-effort coerce to string
        text: str | None = None
        if result is not None:
            if hasattr(result, "output"):
                value = result.output
                text = value if isinstance(value, str) else str(value)
            else:
                text = str(result)
        if text:
            ui.log_final(text)

    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "run":
        return asyncio.run(_run_once_async(args))
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    raise SystemExit(main())
