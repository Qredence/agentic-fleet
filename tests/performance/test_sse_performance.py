#!/usr/bin/env python3
"""Test SSE streaming performance with correlation tracking."""

import json
import time
from typing import Any

import httpx


def test_sse_streaming() -> None:
    """Test SSE streaming with performance measurements."""
    base_url = "http://localhost:8000"

    # Create conversation
    print("Creating conversation...")
    response = httpx.post(
        f"{base_url}/v1/conversations", json={"id": "test-sse-perf"}, timeout=10.0
    )
    conv_data = response.json()
    conversation_id = conv_data["id"]
    print(f"✓ Conversation created: {conversation_id}")

    # Test SSE streaming
    print("\nTesting SSE streaming...")
    start_time = time.time()
    first_event_time = None
    ttft = 0.0  # Initialize to avoid unbound variable warning if no events arrive
    event_count = 0
    correlation_id = None
    last_event_time = start_time
    latencies = []

    payload = {
        "conversation_id": conversation_id,
        "message": "List available workflows",
        "stream": True,
    }

    with (
        httpx.Client(timeout=60.0) as client,
        client.stream(
            "POST", f"{base_url}/v1/chat", json=payload, headers={"Accept": "text/event-stream"}
        ) as stream_response,
    ):
        # Check correlation ID in headers
        correlation_id = stream_response.headers.get("X-Correlation-ID")
        print(f"✓ Correlation ID: {correlation_id}")

        for line in stream_response.iter_lines():
            if not line or line.startswith(":"):
                continue

            if line.startswith("data: "):
                event_time = time.time()
                if first_event_time is None:
                    first_event_time = event_time
                    ttft = (first_event_time - start_time) * 1000
                    print(f"✓ Time to First Token (TTFT): {ttft:.2f}ms")

                # Calculate latency since last event
                event_latency = (event_time - last_event_time) * 1000
                latencies.append(event_latency)
                last_event_time = event_time

                data = line[6:]  # Remove "data: " prefix
                if data == "[DONE]":
                    break

                try:
                    event: dict[str, Any] = json.loads(data)
                    event_count += 1

                    # Check if event has correlation_id
                    event_corr_id = event.get("correlation_id")
                    if event_corr_id and event_corr_id != correlation_id:
                        print(f"⚠️  Event correlation mismatch: {event_corr_id} != {correlation_id}")

                    # Print event summary
                    event_type = event.get("type", "unknown")
                    print(f"  Event {event_count}: {event_type} (+{event_latency:.1f}ms)")

                except json.JSONDecodeError:
                    continue

    total_time = (time.time() - start_time) * 1000
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0

    print(f"\n{'=' * 60}")
    print("Performance Summary:")
    print(f"{'=' * 60}")
    print(f"Correlation ID:     {correlation_id}")
    print(f"Total Events:       {event_count}")
    print(f"Total Time:         {total_time:.2f}ms")
    print(f"TTFT:               {ttft:.2f}ms" if first_event_time else "TTFT:               N/A")
    print(f"Average Latency:    {avg_latency:.2f}ms")
    print(f"Max Latency:        {max_latency:.2f}ms")
    print(f"{'=' * 60}")


if __name__ == "__main__":  # pragma: no cover - manual invocation
    test_sse_streaming()
