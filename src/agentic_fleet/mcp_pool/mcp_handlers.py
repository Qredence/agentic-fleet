"""MCP handlers module.

This module provides handlers for MCP-related actions and callbacks.
It is the preferred implementation that replaces the deprecated
agentic_fleet.mcp_handlers module.
"""

import logging
from typing import Any, Dict, List, Optional

import chainlit as cl

from agentic_fleet.mcp_pool.mcp_factory import create_mcp, get_available_mcp_configs

logger = logging.getLogger(__name__)


@cl.action_callback("activate_mcp")
async def on_activate_mcp(action: cl.Action) -> None:
    """Handle the activate MCP action.

    Args:
        action: The action that triggered this callback
    """
    try:
        # Import here to avoid circular imports
        from agentic_fleet.ui.components.mcp_panel import send_mcp_panel

        # Get the MCP ID from the action value
        mcp_id = action.value
        if not mcp_id:
            await cl.Message(
                content="Error: No MCP ID specified.",
                author="System",
            ).send()
            return

        # Send the MCP panel
        await send_mcp_panel(mcp_id)
    except Exception as e:
        logger.error(f"Error activating MCP: {e}")
        await cl.Message(
            content=f"Error activating MCP: {str(e)}",
            author="System",
        ).send()


@cl.action_callback("connect_mcp")
async def on_connect_mcp(action: cl.Action) -> None:
    """Handle the connect MCP action.

    Args:
        action: The action that triggered this callback
    """
    try:
        # Get the MCP ID from the action value
        mcp_id = action.value
        if not mcp_id:
            await cl.Message(
                content="Error: No MCP ID specified.",
                author="System",
            ).send()
            return

        # Create the MCP instance
        mcp = create_mcp(mcp_id)
        if not mcp:
            await cl.Message(
                content=f"Error: Failed to create MCP instance for {mcp_id}.",
                author="System",
            ).send()
            return

        # Initialize the MCP
        await mcp.initialize()

        # Store the MCP instance in the user session
        mcp_servers = cl.user_session.get("mcp_servers") or []
        mcp_servers.append({
            "id": mcp_id,
            "name": mcp.name,
            "description": mcp.description,
            "type": mcp.__class__.__name__,
            "instance": mcp,
            "tools": [],  # Will be populated later
        })
        cl.user_session.set("mcp_servers", mcp_servers)

        # Send a success message
        await cl.Message(
            content=f"Successfully connected to MCP: {mcp.name}",
            author="MCP Manager",
        ).send()
    except Exception as e:
        logger.error(f"Error connecting to MCP: {e}")
        await cl.Message(
            content=f"Error connecting to MCP: {str(e)}",
            author="System",
        ).send()


@cl.action_callback("disconnect_mcp")
async def on_disconnect_mcp(action: cl.Action) -> None:
    """Handle the disconnect MCP action.

    Args:
        action: The action that triggered this callback
    """
    try:
        # Get the MCP ID from the action value
        mcp_id = action.value
        if not mcp_id:
            await cl.Message(
                content="Error: No MCP ID specified.",
                author="System",
            ).send()
            return

        # Get the MCP servers from the user session
        mcp_servers = cl.user_session.get("mcp_servers") or []

        # Find the MCP server with the specified ID
        for i, server in enumerate(mcp_servers):
            if server.get("id") == mcp_id:
                # Shut down the MCP instance
                mcp_instance = server.get("instance")
                if mcp_instance:
                    await mcp_instance.shutdown()

                # Remove the MCP server from the list
                mcp_servers.pop(i)
                cl.user_session.set("mcp_servers", mcp_servers)

                # Send a success message
                await cl.Message(
                    content=f"Successfully disconnected from MCP: {server.get('name')}",
                    author="MCP Manager",
                ).send()
                return

        # If we get here, the MCP server was not found
        await cl.Message(
            content=f"Error: MCP server with ID {mcp_id} not found.",
            author="System",
        ).send()
    except Exception as e:
        logger.error(f"Error disconnecting from MCP: {e}")
        await cl.Message(
            content=f"Error disconnecting from MCP: {str(e)}",
            author="System",
        ).send()
