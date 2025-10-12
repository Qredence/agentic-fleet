"""
REPL (Read-Eval-Print-Loop) interface for AgenticFleet.

This module provides the interactive command-line interface for users
to interact with the multi-agent system.
"""

import asyncio
import sys

from agenticfleet.config import settings
from agenticfleet.core.logging import get_logger
from agenticfleet.workflows import workflow

logger = get_logger(__name__)


async def run_repl() -> None:
    """
    Run the interactive REPL loop for user interaction.
    """
    while True:
        try:
            user_input = input("🎯 Your task: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("Thank you for using AgenticFleet!")
                break

            if not user_input:
                continue

            logger.info(f"Processing: '{user_input}'")
            print("-" * 50)

            try:
                result = await workflow.run(user_input)

                print("\n" + "=" * 50)
                print("TASK COMPLETED!")
                print("=" * 50)

                if result:
                    print(f"Result:\n{result}")
                else:
                    print("Task completed but no result was returned.")

            except Exception as e:
                logger.error(f"Workflow execution failed: {e}", exc_info=True)
                logger.error(
                    "This might be due to API rate limits, complex tasks, "
                    "or agent coordination failures."
                )
                logger.error("Try simplifying your request or checking your API key and quota.")

            print("\n" + "=" * 70)
            print("Ready for next task...")
            print("=" * 70 + "\n")

        except KeyboardInterrupt:
            logger.warning("Session interrupted by user")
            confirm = input("\nDo you want to exit? (y/n): ").strip().lower()
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

    try:
        if not settings.openai_api_key:
            logger.error("OPENAI_API_KEY environment variable is required")
            logger.error("Please copy .env.example to .env and add your OpenAI API key")
            return 1
    except Exception as e:
        logger.error(f"Configuration Error: {e}", exc_info=True)
        return 1

    logger.info("Initializing multi-agent workflow...")
    logger.info("Workflow ready!")
    logger.info("Agents: Orchestrator, Researcher, Coder, Analyst")
    logger.info("Tools: Web search, Code interpreter, Data analysis")

    print("\n" + "=" * 70)
    print("AGENTICFLEET READY FOR TASK EXECUTION")
    print("=" * 70)
    print("\nExample tasks to try:")
    print("  • 'Research Python machine learning libraries and write example code'")
    print("  • 'Analyze e-commerce trends and suggest visualizations'")
    print("  • 'Write a Python function to process CSV data and explain it'")
    print("\nCommands:")
    print("  - Type your task and press Enter to execute")
    print("  - Type 'quit', 'exit', or 'q' to exit")
    print("  - Press Ctrl+C to interrupt")
    print()

    try:
        asyncio.run(run_repl())
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


def main() -> None:
    """
    Console script entry point.

    This is called when running: uv run agentic-fleet
    """
    sys.exit(run_repl_main())


if __name__ == "__main__":
    main()
