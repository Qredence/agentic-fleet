"""
Demonstration of DSPy + agent-framework integration in AgenticFleet.

This example shows:
1. Creating DSPy-enhanced agents with agent-framework
2. Task enhancement with DSPy signatures
3. Response caching for performance
4. Performance tracking and metrics
5. Streaming execution with timeout management

Usage:
    python examples/dspy_agent_framework_demo.py
"""

import asyncio
import os

# Add src to path for imports
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_framework.openai import OpenAIResponsesClient

from agentic_fleet.agents.base import DSPyEnhancedAgent
from agentic_fleet.tools.tavily_mcp_tool import TavilyMCPTool
from agentic_fleet.utils.logger import setup_logger

# Load environment variables
load_dotenv(override=True)

logger = setup_logger(__name__)


async def demo_basic_usage():
    """Demonstrate basic DSPy-enhanced agent usage."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic DSPy-Enhanced Agent")
    print("=" * 60)

    # Create agent with DSPy enhancement
    client = OpenAIResponsesClient(
        model_id="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    agent = DSPyEnhancedAgent(
        name="ResearcherAgent",
        chat_client=client,
        instructions="Research and provide accurate information with sources",
        tools=TavilyMCPTool(),
        enable_dspy=True,
        cache_ttl=300,
        timeout=30,
    )

    # Execute task with DSPy enhancement
    task = "Who won the 2024 US presidential election?"
    print(f"\n📝 Task: {task}")

    try:
        result = await agent.execute_with_timeout(task)
        result_text = result.text or ""
        print(f"\n✅ Result: {result_text[:500]}...")

        # Show performance stats
        stats = agent.get_performance_stats()
        print("\n📊 Performance Stats:")
        print(f"  - Total executions: {stats['total_executions']}")
        print(f"  - Success rate: {stats['success_rate']:.2%}")
        print(f"  - Avg duration: {stats['avg_duration']:.2f}s")

    except Exception as e:
        logger.error(f"Execution failed: {e}")


async def demo_streaming():
    """Demonstrate streaming execution with DSPy."""
    print("\n" + "=" * 60)
    print("Demo 2: Streaming with DSPy Enhancement")
    print("=" * 60)

    client = OpenAIResponsesClient(
        model_id="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    agent = DSPyEnhancedAgent(
        name="ResearcherAgent",
        chat_client=client,
        instructions="Research and provide accurate information",
        tools=TavilyMCPTool(),
        enable_dspy=True,
    )

    task = "What are the latest developments in AI agents?"
    print(f"\n📝 Task: {task}")
    print("\n🔄 Streaming response:\n")

    try:
        async for event in agent.run_stream_with_dspy(task):
            # Handle different event types from agent-framework
            if hasattr(event, "text") and event.text:
                print(event.text, end="", flush=True)

        print("\n\n✅ Streaming complete")

    except Exception as e:
        logger.error(f"Streaming failed: {e}")


async def demo_caching():
    """Demonstrate response caching."""
    print("\n" + "=" * 60)
    print("Demo 3: Response Caching")
    print("=" * 60)

    client = OpenAIResponsesClient(
        model_id="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    agent = DSPyEnhancedAgent(
        name="ResearcherAgent",
        chat_client=client,
        instructions="Research and provide accurate information",
        tools=TavilyMCPTool(),
        cache_ttl=60,  # 1 minute cache
    )

    task = "What is the capital of France?"

    # First execution
    print(f"\n📝 Task: {task}")
    print("🔄 First execution (no cache)...")
    import time

    start = time.time()
    result1 = await agent.run_cached(task)
    duration1 = time.time() - start
    print(f"✅ Duration: {duration1:.2f}s")
    print(f"   Response: {(result1.text or '')[:200]}...")

    # Second execution (should be cached)
    print("\n🔄 Second execution (should be cached)...")
    start = time.time()
    result2 = await agent.run_cached(task)
    duration2 = time.time() - start
    print(f"✅ Duration: {duration2:.2f}s")
    print(f"   Response: {(result2.text or '')[:200]}...")

    print(f"\n📊 Cache speedup: {duration1 / duration2:.1f}x faster")


async def demo_timeout_handling():
    """Demonstrate timeout handling."""
    print("\n" + "=" * 60)
    print("Demo 4: Timeout Handling")
    print("=" * 60)

    client = OpenAIResponsesClient(
        model_id="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    agent = DSPyEnhancedAgent(
        name="ResearcherAgent",
        chat_client=client,
        instructions="Research comprehensive information",
        tools=TavilyMCPTool(),
        timeout=5,  # Very short timeout for demo
    )

    task = "Write a comprehensive history of artificial intelligence from 1950 to 2024"
    print(f"\n📝 Task: {task}")
    print("⏱️  Timeout: 5 seconds")

    try:
        result = await agent.execute_with_timeout(task, timeout=5)

        additional = getattr(result, "additional_properties", {})
        status = additional.get("status") if isinstance(additional, dict) else None
        if status == "timeout":
            print("\n⏰ Task timed out as expected")
            print(f"   Message: {result.text}")
        else:
            print(f"\n✅ Result: {(result.text or '')[:200]}...")

    except TimeoutError:
        print("\n⏰ Task exceeded timeout")


async def demo_performance_tracking():
    """Demonstrate performance tracking across multiple executions."""
    print("\n" + "=" * 60)
    print("Demo 5: Performance Tracking")
    print("=" * 60)

    client = OpenAIResponsesClient(
        model_id="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    agent = DSPyEnhancedAgent(
        name="QuickAgent",
        chat_client=client,
        instructions="Provide quick, concise answers",
        enable_dspy=True,
    )

    tasks = ["What is 2+2?", "Name the colors of the rainbow", "What is the speed of light?"]

    print("\n🔄 Executing multiple tasks...")

    for i, task in enumerate(tasks, 1):
        print(f"\n  {i}. {task}")
        try:
            result = await agent.execute_with_timeout(task, timeout=15)
            print(f"     ✅ {(result.text or '')[:100]}...")
        except Exception as e:
            print(f"     ❌ Error: {e}")

    # Show aggregated stats
    stats = agent.get_performance_stats()
    print("\n📊 Aggregated Performance Stats:")
    print(f"  - Total executions: {stats['total_executions']}")
    print(f"  - Success rate: {stats['success_rate']:.2%}")
    print(f"  - Average duration: {stats['avg_duration']:.2f}s")
    print(f"  - Min duration: {stats['min_duration']:.2f}s")
    print(f"  - Max duration: {stats['max_duration']:.2f}s")

    # Show bottlenecks
    bottlenecks = agent.performance_tracker.get_bottlenecks(threshold=5.0)
    if bottlenecks:
        print("\n⚠️  Performance Bottlenecks (>5s):")
        for b in bottlenecks:
            print(f"  - {b['agent']}: {b['duration']:.2f}s")


async def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("DSPy + agent-framework Integration Demo")
    print("=" * 60)

    # Check for required API keys
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set in environment")
        return

    if not os.getenv("TAVILY_API_KEY"):
        print("⚠️  TAVILY_API_KEY not set - some demos may fail")

    # Run demos
    await demo_basic_usage()
    await demo_streaming()
    await demo_caching()
    await demo_timeout_handling()
    await demo_performance_tracking()

    print("\n" + "=" * 60)
    print("✅ All demos completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
