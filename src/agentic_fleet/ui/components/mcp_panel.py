"""MCP panel UI components.

This module provides UI components for displaying MCP information.
"""

import logging
from typing import Dict, List, Any, Optional

import chainlit as cl

from agentic_fleet.mcp_handlers import MCP_SERVERS

logger = logging.getLogger(__name__)


async def list_available_mcps() -> None:
    """List available MCP connections and their tools."""
    try:
        # Get connected MCP servers from user session
        mcp_servers = cl.user_session.get("mcp_servers", [])

        if not mcp_servers or len(mcp_servers) == 0:
            await cl.Message(
                content="No MCP servers currently connected. Use the MCP panel to connect to an MCP server.",
                author="MCP Manager"
            ).send()
            return

        # Build a markdown list of all tools
        mcp_tools_list = "# Available MCP Tools\n\n"

        # Process each server
        for server in mcp_servers:
            server_name = server.get("name", "Unknown")
            server_type = server.get("connection_type", "Unknown")
            server_tools = server.get("tools", [])

            mcp_tools_list += f"## {server_name} ({server_type})\n"

            if not server_tools:
                mcp_tools_list += "No tools available from this server.\n\n"
                continue

            for tool in server_tools:
                tool_name = tool.get("name", "Unnamed Tool")
                tool_desc = tool.get("description", "No description available")
                mcp_tools_list += f"- **{tool_name}**: {tool_desc}\n"

            mcp_tools_list += "\n"

        # Send the tools list
        await cl.Message(
            content=mcp_tools_list,
            author="MCP Manager",
        ).send()
    except Exception as e:
        logger.error(f"Error retrieving MCP tools: {e}")
        await cl.Message(
            content=f"Error retrieving MCP tools: {str(e)}",
            author="MCP Manager",
        ).send()


async def call_mcp_tool(server_name: str, tool_name: str, tool_args: Dict[str, Any]) -> Any:
    """Call an MCP tool.
    
    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool to call
        tool_args: Arguments for the tool
        
    Returns:
        The result from the tool execution
    """
    try:
        # Try to get session from module dict first
        if server_name in MCP_SERVERS:
            session = MCP_SERVERS[server_name]["session"]
            
            # Send a message showing what we're calling
            await cl.Message(
                content=f"Calling MCP tool: `{tool_name}` on server `{server_name}`\nArguments: ```json\n{str(tool_args)}\n```",
                author="MCP Manager"
            ).send()
            
            # Call the tool and get the result
            result = await session.call_tool(tool_name, tool_args)
            
            # Send back the result
            result_str = str(result) if result is not None else "No result returned"
            await cl.Message(
                content=f"MCP tool result:\n```json\n{result_str}\n```",
                author="MCP Manager"
            ).send()
                
            return result
        else:
            error_msg = f"MCP server '{server_name}' not connected"
            await cl.Message(content=f"⚠️ {error_msg}", author="MCP Manager").send()
            raise ValueError(error_msg)
            
    except Exception as e:
        error_msg = f"Error calling MCP tool '{tool_name}': {str(e)}"
        logger.error(error_msg)
        
        # Show error in the UI
        await cl.Message(content=f"⚠️ {error_msg}", author="MCP Manager").send()
        raise
