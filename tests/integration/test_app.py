"""Integration tests for the main application."""
import chainlit as cl
import pytest
from chainlit.context import ChainlitContext, context_var
from chainlit.types import ThreadDict
from chainlit.user import User

from agentic_fleet.app import handle_message, setup_chat_settings, update_settings


@pytest.fixture
async def chainlit_context():
    """Set up a mock Chainlit context."""
    thread = ThreadDict(id="test_thread")
    user = User(id="test_user", metadata={})
    session = {"thread": thread, "user": user}
    context = ChainlitContext(session=session)
    context.thread = thread
    token = context_var.set(context)
    yield context
    context_var.reset(token)


@pytest.mark.asyncio
async def test_setup_chat_settings(chainlit_context):
    """Test chat settings initialization."""
    await setup_chat_settings()
    # Add assertions for session state


@pytest.mark.asyncio
async def test_update_settings(chainlit_context):
    """Test settings update."""
    test_settings = {
        "max_rounds": 75,
        "max_time": 15,
        "max_stalls": 3,
        "start_page": "https://example.com",
    }
    await update_settings(test_settings)
    # Add assertions for settings state


@pytest.mark.asyncio
async def test_handle_message(chainlit_context):
    """Test message handling."""
    test_message = cl.Message(
        content="Test message",
        author="user",
    )
    await handle_message(test_message)
    # Add assertions for message handling
