"""
Integration test for SSE streaming endpoint.

This test verifies that the /v1/chat/stream endpoint correctly
streams Server-Sent Events for real-time workflow execution updates.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from httpx_sse import aconnect_sse

from agentic_fleet.api.app import create_app


@pytest.mark.asyncio
async def test_sse_stream_integration() -> None:
    """Test the complete SSE streaming flow with a real conversation."""
    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Create a conversation
        conv_resp = await client.post("/v1/conversations")
        assert conv_resp.status_code == 201
        conversation_id = conv_resp.json()["id"]

        # Step 2: Stream a message
        events_received = []
        deltas_received = []

        async with aconnect_sse(
            client,
            "POST",
            "/v1/chat/stream",
            json={"conversation_id": conversation_id, "message": "Hello world"},
        ) as event_source:
            async for sse in event_source.aiter_sse():
                events_received.append(sse)

                if sse.event == "message":
                    import json

                    data = json.loads(sse.data)
                    if data.get("type") == "delta" and "delta" in data:
                        deltas_received.append(data["delta"])
                    elif data.get("type") == "done":
                        break

        # Step 3: Verify events
        assert len(events_received) >= 2, "Should receive at least delta and done events"
        assert len(deltas_received) > 0, "Should receive at least one delta"

        # Step 4: Verify conversation was updated
        conv_detail = await client.get(f"/v1/conversations/{conversation_id}")
        assert conv_detail.status_code == 200
        conv_data = conv_detail.json()
        assert len(conv_data["messages"]) == 2  # User message + assistant response

        # Verify the assistant message contains the deltas
        assistant_msg = conv_data["messages"][1]
        assert assistant_msg["role"] == "assistant"
        assert assistant_msg["content"] == "".join(deltas_received)


if __name__ == "__main__":
    # Allow running this test standalone for debugging
    asyncio.run(test_sse_stream_integration())
