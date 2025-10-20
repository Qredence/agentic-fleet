"""Command line entry points for the dynamic Magentic workflow."""

from __future__ import annotations

import argparse
import asyncio
import sys

from agenticfleet.core.logging import get_logger

from .factory import create_dynamic_workflow

logger = get_logger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dynamic-fleet",
        description="Run the standalone Magentic workflow with dynamic participant routing.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Task prompt to execute. If omitted, the command reads from standard input.",
    )
    parser.add_argument(
        "--manager-model",
        dest="manager_model",
        help="Override the manager LLM model identifier.",
    )
    parser.add_argument(
        "--manager-instructions",
        dest="manager_instructions",
        help="Override the manager system prompt.",
    )
    parser.add_argument(
        "--progress-ledger-retries",
        dest="progress_ledger_retry_count",
        type=int,
        help="Number of retries when parsing the progress ledger JSON.",
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Disable the optional tool participants (e.g., web search, code interpreter).",
    )
    return parser.parse_args(argv)


def _resolve_prompt(prompt_arg: str | None) -> str:
    if prompt_arg:
        return prompt_arg

    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
        if data:
            return data

    raise SystemExit("No prompt provided. Supply a task as an argument or via standard input.")


async def _run_async(args: argparse.Namespace) -> int:
    include_tools = not args.no_tools
    prompt = _resolve_prompt(args.prompt)

    logger.info(
        "Starting dynamic workflow run",
        extra={
            "prompt_preview": prompt[:80],
            "include_tools": include_tools,
            "manager_model": args.manager_model,
            "progress_ledger_retry_count": args.progress_ledger_retry_count,
        },
    )

    workflow = create_dynamic_workflow(
        include_default_tool_agents=include_tools,
        manager_instructions=args.manager_instructions,
        manager_model=args.manager_model,
        progress_ledger_retry_count=args.progress_ledger_retry_count,
    )

    try:
        result = await workflow.run(prompt)
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        logger.error("Dynamic workflow execution failed", exc_info=True)
        raise SystemExit(f"Workflow execution failed: {exc}") from exc

    output: str | None = None
    if result is not None:
        if hasattr(result, "output"):
            value = getattr(result, "output")
            output = value if isinstance(value, str) else str(value)
        else:
            output = str(result)

    if output:
        print(output)

    logger.info(
        "Dynamic workflow completed",
        extra={
            "output_present": bool(output),
            "output_char_count": len(output) if output else 0,
        },
    )

    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    return asyncio.run(_run_async(args))


if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(main())
