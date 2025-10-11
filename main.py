import asyncio
import logging
import sys

from config.settings import settings
from workflows.magentic_workflow import workflow

logger = logging.getLogger(__name__)


async def run_repl():
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
                    logger.info(f"Result:\n{result}")
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
            confirm = input("Do you want to exit? (y/n): ").strip().lower()
            if confirm in ["y", "yes"]:
                logger.info("Goodbye!")
                break
            else:
                logger.info("Continuing...")
                continue


async def main():
    """
    Main application entry point.
    """
    logger.info("Starting AgenticFleet - Phase 1")
    logger.info("Powered by Microsoft Agent Framework")
    logger.info("Using OpenAI with structured responses")

    try:
        if not settings.openai_api_key:
            logger.error("OPENAI_API_KEY environment variable is required")
            logger.error("Please copy .env.example to .env and add your OpenAI API key")
            sys.exit(1)
    except ValueError as e:
        logger.error(f"Configuration Error: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Initializing multi-agent workflow...")
    logger.info("Workflow ready!")
    logger.info("Agents: Orchestrator, Researcher, Coder, Analyst")
    logger.info("Tools: Web search, Code interpreter, Data analysis")

    print("\n" + "=" * 70)
    logger.info("AGENTICFLEET READY FOR TASK EXECUTION")
    print("=" * 70)
    logger.info("Example tasks to try:")
    logger.info("  • 'Research Python machine learning libraries and write example code'")
    logger.info("  • 'Analyze e-commerce trends and suggest visualizations'")
    logger.info("  • 'Write a Python function to process CSV data and explain it'")
    logger.info("Commands:")
    logger.info("  - Type your task and press Enter to execute")
    logger.info("  - Type 'quit', 'exit', or 'q' to exit")
    logger.info("  - Press Ctrl+C to interrupt")
    print()

    await run_repl()


if __name__ == "__main__":
    asyncio.run(main())
