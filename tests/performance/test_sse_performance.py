"""
Performance tests for SSE streaming endpoint.
"""

import json
import os
import time
from typing import Any

import httpx


def sse_streaming_performance_test(base_url: str) -> None:
    """Test SSE streaming with performance measurements for given base_url."""

    # Create conversation
    print("Creating conversation...")
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        response = client.post("/conversations/create", json={"user_id": "test_user"})
        response.raise_for_status()
        conversation_id = response.json()["conversation_id"]

    print(f"Conversation ID: {conversation_id}\n")

    print("\nTesting SSE streaming...")
    start_time = time.time()
    first_event_time = None
    # ttft is set when first event arrives
    event_count = 0
    correlation_id = None
    last_event_time = start_time
    latencies = []

    with (
        httpx.Client(base_url=base_url, timeout=120.0) as client,
        client.stream(
            "POST",
            "/chat/stream",
            json={
                "conversation_id": conversation_id,
                "message": "What are the key benefits of using Python for data science?",
                "user_id": "test_user",
            },
        ) as stream_response,
    ):
        stream_response.raise_for_status()

        for line in stream_response.iter_lines():
            if not line:
                continue

            # Parse SSE format: "data: {...}"
            if line.startswith("data: "):
                current_time = time.time()
                event_count += 1

                # Record TTFT
                if first_event_time is None:
                    first_event_time = current_time
                    ttft = (first_event_time - start_time) * 1000
                    print(f"First event received! TTFT: {ttft:.2f}ms")

                # Track inter-event latency
                if event_count > 1:
                    latency = (current_time - last_event_time) * 1000
                    latencies.append(latency)

                last_event_time = current_time

                try:
                    data_str = line[6:]  # Skip "data: " prefix
                    data: Any = json.loads(data_str)

                    if isinstance(data, dict):
                        # Track correlation ID from first event
                        if correlation_id is None:
                            correlation_id = data.get("correlation_id")

                        event_type = data.get("type", "unknown")
                        print(f"Event #{event_count}: {event_type}", end="")

                        if event_type == "content_delta":
                            content = data.get("content", "")
                            if content:
                                print(f" - '{content[:50]}...'", end="")

                        print()  # newline

                except json.JSONDecodeError:
                    print(f"Warning: Could not parse event data: {data_str[:100]}")
                    continue

    total_time = (time.time() - start_time) * 1000
    avg_latency = (sum(latencies) / len(latencies)) if latencies else None
    max_latency = max(latencies) if latencies else None

    print(f"\n{'=' * 60}")
    print("Performance Summary:")
    print(f"{'=' * 60}")
    print(f"Correlation ID:     {correlation_id}")
    print(f"Total Events:       {event_count}")
    print(f"Total Time:         {total_time:.2f}ms")
    if first_event_time is not None:
        print(f"TTFT:               {ttft:.2f}ms")
    else:
        print("TTFT:               N/A")
    print(
        f"Average Latency:    {avg_latency:.2f}ms"
        if avg_latency is not None
        else "Average Latency:    N/A"
    )
    print(
        f"Max Latency:        {max_latency:.2f}ms"
        if max_latency is not None
        else "Max Latency:        N/A"
    )
    print(f"{'=' * 60}")


def test_sse_streaming() -> None:
    """Legacy entrypoint. Test using default localhost base_url."""
    base_url = os.environ.get("BASE_URL", "http://localhost:8000")
    sse_streaming_performance_test(base_url)


if __name__ == "__main__":
    # Manual invocation, optionally allow overriding base_url via CLI
    import sys

    base_url = (
        sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BASE_URL", "http://localhost:8000")
    )
    sse_streaming_performance_test(base_url)
