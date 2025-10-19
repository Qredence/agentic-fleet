"""
Example: Workflow as Agent with Reflection and Retry Pattern

This example demonstrates how to use the workflow_as_agent pattern from AgenticFleet.
It shows a cyclic workflow where a Worker generates responses and a Reviewer evaluates
them. If not approved, the Worker regenerates based on feedback until approval.

Usage:
    uv run python examples/workflow_as_agent_example.py
"""

import asyncio

from agenticfleet.workflows.workflow_as_agent import create_workflow_agent, run_workflow_agent


async def basic_example() -> None:
    """Basic usage with the convenience function."""
    print("=" * 70)
    print("EXAMPLE 1: Basic Usage with run_workflow_agent()")
    print("=" * 70)

    await run_workflow_agent(query="Explain quantum computing in simple terms.")


async def custom_models_example() -> None:
    """Use custom models for Worker and Reviewer."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Custom Models")
    print("=" * 70)

    await run_workflow_agent(
        query="Write a Python function to find the longest palindrome substring.",
        worker_model="gpt-4.1-nano",
        reviewer_model="gpt-4.1",
    )




async def streaming_example() -> None:
    """Demonstrate streaming responses with run_stream()."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Direct Agent Usage with Streaming")
    print("=" * 70)

    agent = create_workflow_agent(worker_model="gpt-4.1-nano", reviewer_model="gpt-4.1")

    query = "Compare microservices and monolithic architectures."
    print(f"Query: {query}")
    print("-" * 70)

    async for event in agent.run_stream(query):
        print(f"Event: {event}")

    print("=" * 70)





async def complex_query_example() -> None:
    """Test with a complex technical query."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Complex Technical Query")
    print("=" * 70)

    query = (
        "Write production-ready Python code for parallel reading of 1 million files "
        "from disk with proper error handling, progress tracking, and writing results "
        "to a sorted output file."
    )

    await run_workflow_agent(query=query, worker_model="gpt-4.1-nano", reviewer_model="gpt-4.1")


async def main() -> None:
    """Run all examples."""
    print("Workflow as Agent Examples")
    print("This demonstrates the reflection and retry pattern\n")

    # Run examples
    await basic_example()
    await custom_models_example()
    await streaming_example()
    await complex_query_example()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
