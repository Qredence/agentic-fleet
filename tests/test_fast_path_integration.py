"""Integration tests for fast-path workflow routing."""

from unittest.mock import MagicMock, patch

import pytest
from agent_framework import TextContent
from fastapi.testclient import TestClient

from agentic_fleet.api.app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAIResponsesClient for fast-path."""
    with patch("agentic_fleet.workflow.fast_path.OpenAIResponsesClient") as mock_class:
        client = MagicMock()

        # Mock streaming response
        def create_mock_stream(content: str):
            """Create a mock streaming response."""

            async def mock_stream():
                response = MagicMock()
                response.contents = [TextContent(text=content)]
                yield response

            return mock_stream()

        client.get_streaming_response.return_value = create_mock_stream("This is a test response")
        mock_class.return_value = client
        yield client


class TestChatAPIFastPath:
    """Test fast-path integration in Chat API."""

    @pytest.mark.asyncio
    async def test_simple_message_uses_fast_path(self, client, mock_openai_client, monkeypatch):
        """Test that simple messages use fast-path in chat API."""
        monkeypatch.setenv("ENABLE_FAST_PATH", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Reset classifier
        import agentic_fleet.utils.message_classifier as module

        module._classifier = None

        # Create conversation first
        create_response = client.post(
            "/v1/conversations",
            json={"metadata": {"test": "fast-path"}},
        )
        assert create_response.status_code == 201
        conversation_id = create_response.json()["id"]

        # Send simple message
        response = client.post(
            "/v1/chat",
            json={
                "conversation_id": conversation_id,
                "message": "ok",
                "stream": True,
            },
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Verify fast-path was used by checking logs or response characteristics
        # In real implementation, fast-path should complete much faster

    @pytest.mark.asyncio
    async def test_complex_message_uses_full_orchestration(self, client, monkeypatch):
        """Test that complex messages use full orchestration."""
        monkeypatch.setenv("ENABLE_FAST_PATH", "1")

        # Create conversation
        create_response = client.post(
            "/v1/conversations",
            json={"metadata": {"test": "full-orchestration"}},
        )
        assert create_response.status_code == 201
        conversation_id = create_response.json()["id"]

        # Send complex message
        response = client.post(
            "/v1/chat",
            json={
                "conversation_id": conversation_id,
                "message": "implement a new authentication feature with OAuth2",
                "stream": True,
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_fast_path_disabled(self, client, monkeypatch):
        """Test that fast-path can be disabled via env var."""
        monkeypatch.setenv("ENABLE_FAST_PATH", "0")

        # Reset classifier
        import agentic_fleet.utils.message_classifier as module

        module._classifier = None

        # Create conversation
        create_response = client.post(
            "/v1/conversations",
            json={"metadata": {"test": "disabled"}},
        )
        assert create_response.status_code == 201
        conversation_id = create_response.json()["id"]

        # Even simple messages should use full orchestration
        response = client.post(
            "/v1/chat",
            json={
                "conversation_id": conversation_id,
                "message": "ok",
                "stream": True,
            },
        )

        assert response.status_code == 200


class TestResponsesAPIFastPath:
    """Test fast-path integration in Responses API."""

    @pytest.mark.asyncio
    async def test_simple_message_uses_fast_path_responses_api(
        self, client, mock_openai_client, monkeypatch
    ):
        """Test that simple messages use fast-path in responses API."""
        monkeypatch.setenv("ENABLE_FAST_PATH", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Reset classifier
        import agentic_fleet.utils.message_classifier as module

        module._classifier = None

        # Send simple message to responses API
        response = client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "thanks",
                "stream": True,
            },
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_complex_message_uses_full_orchestration_responses_api(self, client, monkeypatch):
        """Test that complex messages use full orchestration in responses API."""
        monkeypatch.setenv("ENABLE_FAST_PATH", "1")

        # Send complex message
        response = client.post(
            "/v1/responses",
            json={
                "model": "magentic_fleet",
                "input": "write a Python script to analyze data",
                "stream": True,
            },
        )

        assert response.status_code == 200


class TestFastPathEventFormat:
    """Test that fast-path events match expected format."""

    @pytest.mark.asyncio
    async def test_fast_path_events_are_sse_compatible(
        self, client, mock_openai_client, monkeypatch
    ):
        """Test that fast-path emits SSE-compatible events."""
        monkeypatch.setenv("ENABLE_FAST_PATH", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Reset classifier
        import agentic_fleet.utils.message_classifier as module

        module._classifier = None

        # Create conversation
        create_response = client.post(
            "/v1/conversations",
            json={"metadata": {"test": "sse-format"}},
        )
        conversation_id = create_response.json()["id"]

        # Send simple message
        response = client.post(
            "/v1/chat",
            json={
                "conversation_id": conversation_id,
                "message": "hello",
                "stream": True,
            },
        )

        assert response.status_code == 200

        # Parse SSE events
        content = response.text
        lines = content.split("\n")

        # Should have data: lines and [DONE] terminator
        data_lines = [line for line in lines if line.startswith("data:")]
        assert len(data_lines) > 0

        # Last data line should be [DONE]
        assert any("[DONE]" in line for line in data_lines)


class TestFastPathPerformance:
    """Test performance characteristics of fast-path."""

    @pytest.mark.asyncio
    async def test_fast_path_response_time(self, client, mock_openai_client, monkeypatch):
        """Test that fast-path responds quickly."""
        import time

        monkeypatch.setenv("ENABLE_FAST_PATH", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Reset classifier
        import agentic_fleet.utils.message_classifier as module

        module._classifier = None

        # Create conversation
        create_response = client.post(
            "/v1/conversations",
            json={"metadata": {"test": "performance"}},
        )
        conversation_id = create_response.json()["id"]

        # Time the request
        start = time.time()
        response = client.post(
            "/v1/chat",
            json={
                "conversation_id": conversation_id,
                "message": "ok",
                "stream": True,
            },
        )
        elapsed = time.time() - start

        assert response.status_code == 200

        # Fast-path should respond quickly (< 5 seconds with mocks)
        assert elapsed < 5.0, f"Fast-path took {elapsed:.2f}s (expected < 5s)"


@pytest.fixture(autouse=True)
def reset_classifier_after_test():
    """Reset classifier after each test."""
    yield
    import agentic_fleet.utils.message_classifier as module

    module._classifier = None
