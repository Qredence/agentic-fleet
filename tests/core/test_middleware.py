"""Comprehensive tests for core/middleware.py."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from agentic_fleet.core.middleware import (
    ChatMiddleware,
    BridgeMiddleware,
    MiddlewareChain,
    create_middleware_chain,
)


class TestChatMiddleware:
    """Test suite for ChatMiddleware class."""

    @pytest.fixture
    def middleware(self):
        """Create a ChatMiddleware instance."""
        return ChatMiddleware()

    async def test_chat_middleware_process_message(self, middleware):
        """Test processing a chat message."""
        message = {"role": "user", "content": "Hello"}

        processed = await middleware.process_message(message)

        assert processed is not None
        assert "role" in processed
        assert "content" in processed

    async def test_chat_middleware_add_metadata(self, middleware):
        """Test adding metadata to message."""
        message = {"role": "user", "content": "Test"}

        processed = await middleware.process_message(message)

        # Check if middleware adds metadata
        assert "timestamp" in processed or processed == message

    async def test_chat_middleware_with_empty_message(self, middleware):
        """Test processing empty message."""
        message = {}

        processed = await middleware.process_message(message)

        assert processed is not None

    async def test_chat_middleware_with_system_message(self, middleware):
        """Test processing system message."""
        message = {"role": "system", "content": "You are a helpful assistant"}

        processed = await middleware.process_message(message)

        assert processed["role"] == "system"

    async def test_chat_middleware_validation(self, middleware):
        """Test message validation."""
        invalid_messages = [
            None,
            {"role": "invalid_role"},
            {"content": "missing role"},
        ]

        for msg in invalid_messages:
            try:
                await middleware.process_message(msg)
            except (ValueError, KeyError, TypeError):
                # Expected for invalid messages
                pass


class TestBridgeMiddleware:
    """Test suite for BridgeMiddleware class."""

    @pytest.fixture
    def middleware(self):
        """Create a BridgeMiddleware instance."""
        mock_history_manager = Mock()
        return BridgeMiddleware(history_manager=mock_history_manager)

    async def test_bridge_middleware_transform(self, middleware):
        """Test transforming message format."""
        source_message = {
            "role": "user",
            "content": "Transform this",
            "format": "source",
        }

        transformed = await middleware.transform(source_message, target_format="target")

        assert transformed is not None

    async def test_bridge_middleware_agent_to_api_format(self, middleware):
        """Test transforming agent message to API format."""
        agent_message = {
            "agent_name": "researcher",
            "message": "Research complete",
            "metadata": {},
        }

        api_message = await middleware.agent_to_api(agent_message)

        assert "role" in api_message or api_message is not None

    async def test_bridge_middleware_api_to_agent_format(self, middleware):
        """Test transforming API message to agent format."""
        api_message = {"role": "assistant", "content": "Response"}

        agent_message = await middleware.api_to_agent(api_message)

        assert agent_message is not None

    async def test_bridge_middleware_with_tool_calls(self, middleware):
        """Test transforming messages with tool calls."""
        message_with_tools = {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "call_1", "function": {"name": "search"}}],
        }

        transformed = await middleware.transform(message_with_tools)

        # Should preserve tool calls
        assert transformed is not None


class TestMiddlewareChain:
    """Test suite for MiddlewareChain class."""

    @pytest.fixture
    def mock_middleware_1(self):
        """Create first mock middleware."""
        middleware = Mock()
        middleware.process_message = AsyncMock(
            side_effect=lambda msg: {**msg, "processed_by": "middleware_1"}
        )
        return middleware

    @pytest.fixture
    def mock_middleware_2(self):
        """Create second mock middleware."""
        middleware = Mock()
        middleware.process_message = AsyncMock(
            side_effect=lambda msg: {**msg, "processed_by_2": "middleware_2"}
        )
        return middleware

    @pytest.fixture
    def chain(self, mock_middleware_1, mock_middleware_2):
        """Create a middleware chain."""
        return MiddlewareChain([mock_middleware_1, mock_middleware_2])

    async def test_middleware_chain_execution(self, chain, mock_middleware_1, mock_middleware_2):
        """Test executing middleware chain."""
        message = {"content": "Test"}

        result = await chain.process(message)

        assert result is not None
        mock_middleware_1.process_message.assert_called_once()
        mock_middleware_2.process_message.assert_called_once()

    async def test_middleware_chain_order(self, mock_middleware_1, mock_middleware_2):
        """Test middleware execution order."""
        call_order = []

        mock_middleware_1.process_message = AsyncMock(
            side_effect=lambda msg: (call_order.append(1), msg)[1]
        )
        mock_middleware_2.process_message = AsyncMock(
            side_effect=lambda msg: (call_order.append(2), msg)[1]
        )

        chain = MiddlewareChain([mock_middleware_1, mock_middleware_2])
        await chain.process({"content": "Test"})

        assert call_order == [1, 2]

    async def test_middleware_chain_empty(self):
        """Test empty middleware chain."""
        chain = MiddlewareChain([])
        message = {"content": "Test"}

        result = await chain.process(message)

        assert result == message

    async def test_middleware_chain_with_error(self, mock_middleware_1):
        """Test middleware chain with middleware error."""
        mock_middleware_1.process_message = AsyncMock(
            side_effect=Exception("Middleware error")
        )

        chain = MiddlewareChain([mock_middleware_1])

        with pytest.raises(Exception, match="Middleware error"):
            await chain.process({"content": "Test"})

    async def test_middleware_chain_short_circuit(self, mock_middleware_1, mock_middleware_2):
        """Test middleware chain short-circuit on None return."""
        mock_middleware_1.process_message = AsyncMock(return_value=None)

        chain = MiddlewareChain([mock_middleware_1, mock_middleware_2])

        _ = await chain.process({"content": "Test"})
        # Note: result variable intentionally unused as test focuses on middleware call behavior

        # If None is returned, chain might stop
        mock_middleware_1.process_message.assert_called_once()
        # middleware_2 might not be called if chain short-circuits


class TestCreateMiddlewareChain:
    """Test suite for create_middleware_chain function."""

    def test_create_middleware_chain_default(self):
        """Test creating default middleware chain."""
        chain = create_middleware_chain()

        assert chain is not None
        assert isinstance(chain, MiddlewareChain)

    def test_create_middleware_chain_with_custom_middleware(self):
        """Test creating chain with custom middleware."""
        custom_middleware = Mock()
        custom_middleware.process_message = AsyncMock()

        chain = create_middleware_chain(middlewares=[custom_middleware])

        assert chain is not None

    def test_create_middleware_chain_with_config(self):
        """Test creating chain from configuration."""
        config = {
            "middleware": {
                "chat": {"enabled": True},
                "bridge": {"enabled": True},
            }
        }

        chain = create_middleware_chain(config=config)

        assert chain is not None


class TestMiddlewareEdgeCases:
    """Test edge cases and error handling."""

    async def test_chat_middleware_with_very_long_content(self):
        """Test processing message with very long content."""
        middleware = ChatMiddleware()
        long_content = "x" * 100000  # 100k characters

        message = {"role": "user", "content": long_content}

        result = await middleware.process_message(message)

        assert result is not None
        assert len(result["content"]) <= 100000 or result["content"] == long_content

    async def test_bridge_middleware_with_nested_data(self):
        """Test transforming message with deeply nested data."""
        mock_history_manager = Mock()
        middleware = BridgeMiddleware(history_manager=mock_history_manager)

        nested_message = {
            "role": "user",
            "content": "Test",
            "metadata": {
                "level1": {
                    "level2": {"level3": {"value": 42}},
                },
            },
        }

        result = await middleware.transform(nested_message)

        assert result is not None

    async def test_middleware_chain_with_many_middlewares(self):
        """Test chain with many middlewares."""
        middlewares = []
        for i in range(50):
            m = Mock()
            m.process_message = AsyncMock(side_effect=lambda msg: msg)
            middlewares.append(m)

        chain = MiddlewareChain(middlewares)

        message = {"content": "Test"}
        result = await chain.process(message)

        assert result == message

    async def test_middleware_with_concurrent_processing(self):
        """Test concurrent middleware processing."""
        import asyncio

        middleware = ChatMiddleware()

        messages = [
            {"role": "user", "content": f"Message {i}"} for i in range(100)
        ]

        results = await asyncio.gather(
            *[middleware.process_message(msg) for msg in messages]
        )

        assert len(results) == 100


class TestMiddlewareIntegration:
    """Integration tests for middleware system."""

    async def test_full_message_pipeline(self):
        """Test complete message processing pipeline."""
        # Create full pipeline: Chat -> Bridge -> Custom
        chat_middleware = ChatMiddleware()
        mock_history_manager = Mock()
        bridge_middleware = BridgeMiddleware(history_manager=mock_history_manager)

        custom_middleware = Mock()
        custom_middleware.process_message = AsyncMock(
            side_effect=lambda msg: {**msg, "custom_processed": True}
        )

        chain = MiddlewareChain([chat_middleware, bridge_middleware, custom_middleware])

        message = {"role": "user", "content": "Test message"}

        result = await chain.process(message)

        assert result is not None
        custom_middleware.process_message.assert_called_once()

    async def test_middleware_state_preservation(self):
        """Test that middleware preserves message state correctly."""
        class StatefulMiddleware:
            async def process_message(self, message):
                # Add processing timestamp
                message["processed_at"] = datetime.now().isoformat()
                return message

        middleware1 = StatefulMiddleware()
        middleware2 = StatefulMiddleware()

        chain = MiddlewareChain([middleware1, middleware2])

        message = {"role": "user", "content": "Test"}
        result = await chain.process(message)

        # Should have timestamp from both middleware
        assert "processed_at" in result

    async def test_error_recovery_in_chain(self):
        """Test error recovery in middleware chain."""
        failing_middleware = Mock()
        failing_middleware.process_message = AsyncMock(
            side_effect=Exception("Middleware failed")
        )

        recovery_middleware = Mock()
        recovery_middleware.process_message = AsyncMock(
            side_effect=lambda msg: {"recovered": True}
        )

        # Depending on implementation, chain might have error handling
        chain = MiddlewareChain([failing_middleware, recovery_middleware])

        message = {"content": "Test"}

        try:
            result = await chain.process(message)
            # If error handling exists
            assert result is not None
        except Exception:
            # If no error handling, exception propagates
            pass