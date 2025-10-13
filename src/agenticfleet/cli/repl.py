"""
REPL (Read-Eval-Print-Loop) interface for AgenticFleet.

This module provides the interactive command-line interface for users
to interact with the multi-agent system.
"""

import asyncio
import sys
from datetime import datetime

from agenticfleet.config import settings
from agenticfleet.core.logging import get_logger
from agenticfleet.workflows import workflow

logger = get_logger(__name__)


async def handle_checkpoint_command(command: str) -> bool:
    """
    Handle checkpoint-related commands.

    Args:
        command: The command string to handle

    Returns:
        True if command was handled, False otherwise
    """
    parts = command.split()

    if parts[0] == "checkpoints" or parts[0] == "list-checkpoints":
        # List all checkpoints
        checkpoints = await workflow.list_checkpoints()
        if not checkpoints:
            print("No checkpoints found.")
        else:
            print(f"\n{'=' * 80}")
            print(f"Available Checkpoints ({len(checkpoints)})")
            print("=" * 80)
            for cp in checkpoints:
                timestamp = cp.get("timestamp", "unknown")
                # Format timestamp if it's an ISO string
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # If timestamp is not valid ISO format, use as-is
                    pass

                print(f"\nCheckpoint ID: {cp.get('checkpoint_id')}")
                print(f"  Workflow ID: {cp.get('workflow_id')}")
                print(f"  Timestamp:   {timestamp}")
                print(f"  Round:       {cp.get('current_round')}")
                metadata = cp.get("metadata", {})
                if metadata:
                    print(f"  Status:      {metadata.get('status', 'unknown')}")
            print("=" * 80)
        return True

    elif parts[0] == "resume" and len(parts) > 1:
        # Resume from checkpoint
        checkpoint_id = parts[1]
        print(f"\nAttempting to resume from checkpoint: {checkpoint_id}")

        # User needs to provide new input after resuming
        user_input = input("🎯 Your task (continuing from checkpoint): ").strip()
        if not user_input:
            print("No input provided. Resuming cancelled.")
            return True

        print("-" * 50)

        try:
            result = await workflow.run(user_input, resume_from_checkpoint=checkpoint_id)

            print("\n" + "=" * 50)
            print("TASK COMPLETED (RESUMED FROM CHECKPOINT)!")
            print("=" * 50)

            if result:
                print(f"Result:\n{result}")
            else:
                print("Task completed but no result was returned.")

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            print(f"Error resuming workflow: {e}")

        return True

    return False


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

            # Handle checkpoint commands
            if user_input.startswith(("checkpoints", "list-checkpoints", "resume")):
                handled = await handle_checkpoint_command(user_input)
                if handled:
                    continue

            safe_user_input = user_input.replace("\r", "").replace("\n", "")
            logger.info(f"Processing: '{safe_user_input}'")
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
    print("  - Type 'checkpoints' or 'list-checkpoints' to view saved checkpoints")
    print("  - Type 'resume <checkpoint_id>' to resume from a checkpoint")
    print("  - Type 'quit', 'exit', or 'q' to exit")
    print("  - Press Ctrl+C to interrupt")

    # Show checkpoint status
    checkpoint_config = settings.workflow_config.get("workflow", {}).get("checkpointing", {})
    if checkpoint_config.get("enabled", False):
        storage_path = checkpoint_config.get("storage_path", "./checkpoints")
        print(f"\n✓ Checkpointing enabled (storage: {storage_path})")
    else:
        print("\n⚠ Checkpointing disabled")
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
