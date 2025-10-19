#!/usr/bin/env python3
"""
Quick test script for the /v1/workflow/reflection endpoint.

This script demonstrates how to use the dedicated reflection workflow endpoint
with real-time streaming of Worker and Reviewer interactions.

Run with: uv run python examples/test_reflection_api.py
"""

import json
import sys

import httpx


def test_reflection_endpoint() -> bool:
    """Test the reflection workflow endpoint with streaming."""
    url = "http://localhost:8000/v1/workflow/reflection"

    payload = {
        "query": "Explain quantum entanglement in simple terms.",
        "worker_model": "gpt-4.1-nano",
        "reviewer_model": "gpt-4.1",
    }

    print("=" * 70)
    print("Testing Reflection Workflow Endpoint")
    print("=" * 70)
    print(f"\nEndpoint: {url}")
    print(f"Query: {payload['query']}")
    print(f"Worker Model: {payload['worker_model']}")
    print(f"Reviewer Model: {payload['reviewer_model']}")
    print("\n" + "-" * 70)
    print("Streaming response...")
    print("-" * 70 + "\n")

    try:
        with httpx.Client(timeout=60.0) as client:
            with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    print(f"Error: HTTP {response.status_code}")
                    print(response.text)
                    return False

                accumulated = ""
                event_count = 0

                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix

                        if data == "[DONE]":
                            print("\n" + "-" * 70)
                            print("Stream completed")
                            break

                        try:
                            event = json.loads(data)
                            event_count += 1

                            if event.get("type") == "response.output_text.delta":
                                delta = event.get("delta", "")
                                accumulated += delta
                                print(delta, end="", flush=True)

                            elif event.get("type") == "response.done":
                                print("\n\n" + "-" * 70)
                                print("Response completed")
                                print(f"Conversation ID: {event.get('conversation_id')}")
                                print(f"Message ID: {event.get('message_id')}")
                                usage = event.get("usage", {})
                                print(f"Usage: {usage}")

                            elif event.get("type") == "error":
                                print(f"\n\nError: {event.get('error')}")
                                return False

                        except json.JSONDecodeError:
                            continue

                print("\n" + "=" * 70)
                print(f"Total events: {event_count}")
                print(f"Response length: {len(accumulated)} characters")
                print("=" * 70)
                return True

    except httpx.ConnectError:
        print("❌ Could not connect to backend at http://localhost:8000")
        print("\nPlease start the backend first:")
        print("  make haxui-server")
        print("  or: uv run uvicorn agenticfleet.haxui.api:app --reload --port 8000")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def main() -> int:
    """Main entry point."""
    success = test_reflection_endpoint()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
