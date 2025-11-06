#!/usr/bin/env python3
"""Test script to inspect gpt-5-mini reasoning token structure."""

import asyncio
import os

from agent_framework import ChatMessage, ChatOptions, TextContent, TextReasoningContent
from agent_framework.openai import OpenAIResponsesClient


async def test_reasoning_structure() -> None:
    """Test gpt-5-mini response with reasoning enabled."""

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return

    # Create client with reasoning parameters
    client = OpenAIResponsesClient(
        model_id="gpt-5-mini",
        api_key=api_key,
        reasoning_effort="medium",
        reasoning_verbosity="normal",
    )

    print("Testing gpt-5-mini with reasoning enabled...")
    print("Model: gpt-5-mini")
    print("Reasoning effort: medium")
    print("Reasoning verbosity: normal")
    print("-" * 80)

    # Test message
    messages = [
        ChatMessage(
            role="user",
            contents=[TextContent(text="What is 15 * 24? Show your reasoning step by step.")],
        )
    ]

    chat_options = ChatOptions(model_id="gpt-5-mini")

    # Test streaming response
    print("\nStreaming response:")
    print("-" * 80)

    try:
        async for update in client.get_streaming_response(
            messages=messages, chat_options=chat_options
        ):
            # Inspect the update object
            print(f"\nUpdate type: {type(update).__name__}")
            print(
                f"Update attributes: {[attr for attr in dir(update) if not attr.startswith('_')]}"
            )

            # Check contents
            if hasattr(update, "contents"):
                for i, content in enumerate(update.contents):
                    print(f"\nContent {i} type: {type(content).__name__}")
                    print(
                        f"Content {i} attributes: {[attr for attr in dir(content) if not attr.startswith('_')]}"
                    )

                    # Check if this is TextReasoningContent (reasoning token)
                    if isinstance(content, TextReasoningContent):
                        print("*** REASONING CONTENT FOUND ***")
                        print(f"Reasoning text: {content.text[:200] if content.text else None}")
                    elif isinstance(content, TextContent):
                        print(f"Text: {content.text[:100] if content.text else None}")

            # Try to serialize (optional, for debugging)
            try:
                import json as json_mod

                if hasattr(update, "to_dict"):
                    json_data = update.to_dict()
                    print(
                        f"\nJSON structure: {json_mod.dumps(json_data, indent=2, default=str)[:500]}"
                    )
            except Exception:
                pass  # Skip serialization if not possible

    except Exception as e:
        print(f"Error during streaming: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_reasoning_structure())
