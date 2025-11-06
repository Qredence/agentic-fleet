"""Tests for fast-path workflow implementation."""

from unittest.mock import MagicMock, patch

import pytest
from agent_framework import TextContent

from agentic_fleet.workflow.fast_path import FastPathWorkflow, create_fast_path_workflow


class TestFastPathWorkflow:
    """Test suite for FastPathWorkflow class."""

    @pytest.fixture
    def mock_text_content(self):
        """Create a mock TextContent."""

        def create_content(text):
            return TextContent(text=text) if text else TextContent(text="")

        return create_content

    @pytest.fixture
    def mock_response(self, mock_text_content):
        """Create a mock ChatMessage response."""

        def create_response(text):
            response = MagicMock()
            response.contents = [mock_text_content(text)]
            return response

        return create_response

    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenAIResponsesClient."""
        client = MagicMock()  # Use MagicMock instead of AsyncMock
        return client

    @pytest.fixture
    def workflow(self, mock_client):
        """Create a FastPathWorkflow instance with mock client."""
        return FastPathWorkflow(client=mock_client, model="gpt-5-mini")

    @pytest.mark.asyncio
    async def test_workflow_initialization(self):
        """Test workflow initialization with default parameters."""
        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test-key",
            },
        ):
            workflow = FastPathWorkflow()
            assert workflow.model == "gpt-5-mini"

    @pytest.mark.asyncio
    async def test_workflow_initialization_custom_model(self):
        """Test workflow initialization with custom model from env."""
        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test-key",
                "FAST_PATH_MODEL": "gpt-4o-mini",
            },
        ):
            workflow = FastPathWorkflow()
            assert workflow.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_create_client_missing_api_key(self):
        """Test that missing API key raises ValueError."""
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="OPENAI_API_KEY"),
        ):
            FastPathWorkflow()

    @pytest.mark.asyncio
    async def test_create_client_with_base_url(self):
        """Test that base_url is used when provided."""
        with (
            patch("agentic_fleet.workflow.fast_path.OpenAIResponsesClient") as mock_client_class,
            patch.dict(
                "os.environ",
                {"OPENAI_API_KEY": "test-key", "OPENAI_BASE_URL": "https://custom.openai.com"},
            ),
        ):
            FastPathWorkflow()
            # Verify OpenAIResponsesClient was called with base_url
            mock_client_class.assert_called_once_with(
                model_id="gpt-5-mini",
                api_key="test-key",
                base_url="https://custom.openai.com",
            )

    @pytest.mark.asyncio
    async def test_run_streams_delta_events(self, workflow, mock_client, mock_response):
        """Test that run() streams delta events correctly."""

        # Mock streaming response with TextContent
        async def mock_stream():
            yield mock_response("Hello")
            yield mock_response(" world")
            yield mock_response("!")

        # Set the mock to return the async generator directly
        mock_client.get_streaming_response.return_value = mock_stream()

        # Run workflow
        events = []
        async for event in workflow.run("test message"):
            events.append(event)

        # Verify events
        assert len(events) == 4  # 3 deltas + 1 done

        # Check delta events
        assert events[0]["type"] == "message.delta"
        assert events[0]["data"]["delta"] == "Hello"
        assert events[0]["data"]["agent_id"] == "fast-path"

        assert events[1]["type"] == "message.delta"
        assert events[1]["data"]["delta"] == " world"

        assert events[2]["type"] == "message.delta"
        assert events[2]["data"]["delta"] == "!"

        # Check done event
        assert events[3]["type"] == "message.done"
        assert events[3]["data"]["content"] == "Hello world!"
        assert events[3]["data"]["agent_id"] == "fast-path"
        assert events[3]["data"]["metadata"]["fast_path"] is True
        assert events[3]["data"]["metadata"]["model"] == "gpt-5-mini"

    @pytest.mark.asyncio
    async def test_run_accumulates_content(self, workflow, mock_client, mock_response):
        """Test that content is accumulated correctly."""

        async def mock_stream():
            yield mock_response("test")

        mock_client.get_streaming_response.return_value = mock_stream()

        events = []
        async for event in workflow.run("test"):
            events.append(event)

        # Check accumulated content in delta
        assert events[0]["data"]["accumulated"] == "test"

        # Check final content in done event
        assert events[1]["data"]["content"] == "test"

    @pytest.mark.asyncio
    async def test_run_calls_openai_with_correct_parameters(
        self, workflow, mock_client, mock_response
    ):
        """Test that OpenAIResponsesClient is called with correct parameters."""

        async def mock_stream():
            yield mock_response("response")

        mock_client.get_streaming_response.return_value = mock_stream()

        async for _ in workflow.run("test message"):
            pass

        # Verify get_streaming_response call
        mock_client.get_streaming_response.assert_called_once()
        call_kwargs = mock_client.get_streaming_response.call_args.kwargs

        # Check messages structure
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        # Role is an enum, so check the value
        assert messages[0].role.value == "user"
        # TextContent should have the message
        assert len(messages[0].contents) == 1
        assert messages[0].contents[0].text == "test message"

        # Check chat_options
        chat_options = call_kwargs["chat_options"]
        assert chat_options.model_id == "gpt-5-mini"

    @pytest.mark.asyncio
    async def test_run_handles_empty_chunks(self, workflow, mock_client, mock_text_content):
        """Test that empty chunks are handled gracefully."""
        # Mock response with None content
        empty_response = MagicMock()
        empty_response.contents = [mock_text_content(None)]

        # Mock response with actual content
        content_response = MagicMock()
        content_response.contents = [mock_text_content("content")]

        async def mock_stream():
            yield empty_response
            yield content_response

        mock_client.get_streaming_response.return_value = mock_stream()

        events = []
        async for event in workflow.run("test"):
            events.append(event)

        # Should only emit events for non-empty content
        assert len(events) == 2  # 1 delta + 1 done
        assert events[0]["data"]["delta"] == "content"

    @pytest.mark.asyncio
    async def test_run_emits_error_on_exception(self, workflow, mock_client):
        """Test that errors are emitted as events."""
        mock_client.get_streaming_response.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            events = []
            async for event in workflow.run("test"):
                events.append(event)

            # Should have emitted error event before raising
            assert any(e["type"] == "error" for e in events)
            error_event = next(e for e in events if e["type"] == "error")
            assert "Fast-path error" in error_event["data"]["message"]


class TestCreateFastPathWorkflow:
    """Test suite for create_fast_path_workflow factory function."""

    @pytest.mark.asyncio
    async def test_creates_workflow_with_defaults(self):
        """Test factory creates workflow with default parameters."""
        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test-key",
            },
        ):
            workflow = create_fast_path_workflow()
            assert isinstance(workflow, FastPathWorkflow)
            assert workflow.model == "gpt-5-mini"

    @pytest.mark.asyncio
    async def test_creates_workflow_with_custom_parameters(self):
        """Test factory accepts custom parameters."""
        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test-key",
            },
        ):
            workflow = create_fast_path_workflow(model="custom-model")
            assert workflow.model == "custom-model"
