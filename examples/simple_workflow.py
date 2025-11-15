"""
Simple example of using the DSPy-enhanced supervisor workflow.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

from agentic_fleet.workflows.supervisor_workflow import (
    create_supervisor_workflow,
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Load environment variables
load_dotenv()


async def main():
    """Run a simple workflow example."""

    print("🚀 Initializing DSPy-Enhanced Supervisor Workflow...")

    # Create workflow
    workflow = await create_supervisor_workflow(compile_dspy=True)

    # Define task
    task = """
    Write a comprehensive guide on getting started with Python programming.
    Include:
    1. Installation instructions
    2. Basic syntax examples
    3. Common use cases
    4. Best practices
    """

    print(f"\n📋 Task: {task}")
    print("\n" + "=" * 50)
    print("Starting workflow execution...")
    print("=" * 50 + "\n")

    # Execute workflow
    result = await workflow.run(task)

    # Display results
    print("\n" + "=" * 50)
    print("WORKFLOW COMPLETED")
    print("=" * 50)
    print(f"\n📊 Quality Score: {result['quality']['score']}/10")
    print(f"📍 Execution Mode: {result['routing']['mode']}")
    print(f"👥 Agents Used: {', '.join(result['routing']['assigned_to'])}")
    print(f"\n📄 Result:\n{result['result'][:500]}...")

    # Show execution summary
    summary = result["execution_summary"]
    print("\n📈 Execution Summary:")
    print(f"  - Total Routings: {summary['total_routings']}")
    print(f"  - Routing History: {len(summary['routing_history'])} decisions")


if __name__ == "__main__":
    asyncio.run(main())
