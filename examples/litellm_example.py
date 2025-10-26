"""
Example: Using LiteLLM with AgenticFleet

This example demonstrates how to use LiteLLM to run agents with different
LLM providers (OpenAI, Anthropic, etc.).

Run this example with:
    uv run python examples/litellm_example.py
"""

import asyncio
import os

from agenticfleet.agents.researcher import create_researcher_agent
from agenticfleet.config import settings


async def main():
    """Demonstrate LiteLLM usage with different providers."""

    print("=== LiteLLM Integration Example ===\n")

    # Example 1: Using OpenAI via LiteLLM
    print("1. Using OpenAI via LiteLLM:")
    print("   Set USE_LITELLM=true and LITELLM_MODEL=gpt-4o-mini\n")

    # Example 2: Using Anthropic via LiteLLM
    print("2. Using Anthropic via LiteLLM:")
    print("   Set USE_LITELLM=true and LITELLM_MODEL=anthropic/claude-3-5-sonnet-20241022")
    print("   Set ANTHROPIC_API_KEY=your-key\n")

    # Show current configuration
    print("Current Configuration:")
    print(f"  USE_LITELLM: {settings.use_litellm}")
    print(f"  LITELLM_MODEL: {settings.litellm_model}")
    print(f"  LITELLM_BASE_URL: {settings.litellm_base_url or 'Not set'}")

    if not settings.use_litellm:
        print("\n⚠️  LiteLLM is not enabled. Using default OpenAI client.")
        print("   To enable LiteLLM, set USE_LITELLM=true in your .env file\n")
    else:
        print(f"\n✓ LiteLLM is enabled with model: {settings.litellm_model}\n")

    # Check if we have API keys
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    if settings.use_litellm:
        # Check for provider-specific keys
        has_api_key = has_api_key or bool(
            os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("AZURE_API_KEY")
            or settings.litellm_api_key
        )

    if not has_api_key:
        print("⚠️  No API keys found in environment.")
        print("   To test the agent, set the appropriate API key:")
        print("   - OPENAI_API_KEY for OpenAI models")
        print("   - ANTHROPIC_API_KEY for Anthropic models")
        print("   - AZURE_API_KEY for Azure models")
        print("\nExample configuration saved successfully!")
        return

    # Create an agent (will use LiteLLM if enabled)
    print("Creating researcher agent...")
    agent = create_researcher_agent()
    print(f"✓ Agent created: {agent.name}\n")

    # Note: Actually running the agent would require a valid API key
    print("Agent is ready to use!")
    print(
        "To test the agent, ensure you have the appropriate API keys set and call agent.run()"
    )


if __name__ == "__main__":
    asyncio.run(main())
