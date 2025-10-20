"""Test the dedicated workflow_as_agent reflection endpoint."""

import httpx
import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reflection_workflow_endpoint():
    """Test the /v1/workflow/reflection endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/v1/workflow/reflection",
            json={"query": "What is 2+2? Be concise."},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Collect SSE events
        events = []
        for line in response.text.split("\n"):
            if line.startswith("data: ") and line != "data: [DONE]":
                events.append(line[6:])  # Remove "data: " prefix

        assert len(events) > 0, "Expected at least one SSE event"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reflection_workflow_with_custom_models():
    """Test reflection workflow with custom model parameters."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/v1/workflow/reflection",
            json={
                "query": "Explain photosynthesis briefly.",
                "worker_model": "gpt-4.1-nano",
                "reviewer_model": "gpt-4.1",
            },
        )

        assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reflection_workflow_missing_query():
    """Test that missing query returns 400."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/workflow/reflection",
            json={},
        )

        assert response.status_code == 400
        data = response.json()
        assert "query" in data["detail"].lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reflection_workflow_with_conversation():
    """Test reflection workflow with conversation persistence."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create a conversation first
        conv_response = await client.post("http://localhost:8000/v1/conversations", json={})
        assert conv_response.status_code == 201
        conversation_id = conv_response.json()["id"]

        # Use the conversation in workflow
        response = await client.post(
            "http://localhost:8000/v1/workflow/reflection",
            json={"query": "What is Python?", "conversation_id": conversation_id},
        )

        assert response.status_code == 200


if __name__ == "__main__":
    print("Testing /v1/workflow/reflection endpoint...")
    print("=" * 60)
    print("\nNote: Backend must be running on http://localhost:8000")
    print("\nRun with: uv run pytest tests/test_reflection_endpoint.py -v")
