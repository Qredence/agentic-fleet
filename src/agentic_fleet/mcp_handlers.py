"""MCP connection handlers for AgenticFleet.

This module contains handlers for Model Context Protocol (MCP) connections.
"""

import logging
from typing import Any, Dict, List, Optional

import chainlit as cl

# Initialize logger
logger = logging.getLogger(__name__)

# Store MCP server connections
MCP_SERVERS = {}

@cl.on_mcp_connect
async def on_mcp_connect(connection, session):
    """Handler for when an MCP connection is established.
    
    This is called when a new MCP server connection is established.
    It records the server details and retrieves available tools.
    
    Args:
        connection: The connection details (has name and possibly type)
        session: The MCP client session for making requests
    """
    try:
        # Get connection type safely - some connection objects don't have type
        connection_type = getattr(connection, "type", "stdio")
        
        # Log the connection
        logger.info(f"MCP connection established: {connection.name}")
        
        # List available tools
        tools_result = await session.list_tools()
        
        # Extract tool information
        tools = []
        for tool in tools_result.tools:
            tool_info = {
                "name": tool.name,
                "description": getattr(tool, "description", "No description available"),
                "input_schema": getattr(tool, "inputSchema", {})
            }
            tools.append(tool_info)
        
        # Store server info in user session
        server_info = {
            "name": connection.name,
            "connection_type": connection_type, 
            "tools": tools
        }
        
        # Store in user session
        servers = cl.user_session.get("mcp_servers", [])
        servers = [s for s in servers if s.get("name") != connection.name]  # Remove previous if exists
        servers.append(server_info)
        cl.user_session.set("mcp_servers", servers)
        
        # Also store in local module dict for easier access
        MCP_SERVERS[connection.name] = {
            "info": server_info,
            "session": session
        }
        
        # Send confirmation message
        tools_count = len(tools)
        await cl.Message(
            content=f"✅ Successfully connected to MCP server '{connection.name}' with {tools_count} available tools.",
            author="MCP Manager"
        ).send()
        
    except Exception as e:
        logger.error(f"Error during MCP connection: {e}")
        await cl.Message(
            content=f"⚠️ Error connecting to MCP server: {str(e)}",
            author="MCP Manager"
        ).send()


@cl.on_mcp_disconnect
async def on_mcp_disconnect(name, session):
    """Handler for when an MCP connection is terminated.
    
    Args:
        name: The name of the MCP connection
        session: The MCP client session
    """
    try:
        # Log disconnection
        logger.info(f"MCP connection terminated: {name}")
        
        # Remove from user session
        servers = cl.user_session.get("mcp_servers", [])
        servers = [s for s in servers if s.get("name") != name]
        cl.user_session.set("mcp_servers", servers)
        
        # Remove from local dict
        if name in MCP_SERVERS:
            del MCP_SERVERS[name]
        
        # Send confirmation message
        await cl.Message(
            content=f"Disconnected from MCP server '{name}'.",
            author="MCP Manager"
        ).send()
        
    except Exception as e:
        logger.error(f"Error during MCP disconnection: {e}")


@cl.step(name="call_mcp_tool")
async def call_mcp_tool(server_name: str, tool_name: str, tool_args: Dict[str, Any]) -> Any:
    """Call an MCP tool with the given arguments.
    
    This function can be used as part of a step to call MCP tools.
    
    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool to call
        tool_args: Arguments for the tool
        
    Returns:
        The result from the tool execution
    """
    try:
        # Try to get session from module dict first (most reliable)
        if server_name in MCP_SERVERS:
            session = MCP_SERVERS[server_name]["session"]
        else:
            # Fall back to context methods if available
            for attr_name in ["get_mcp_session", "mcp_sessions"]:
                if hasattr(cl.context, attr_name):
                    attr = getattr(cl.context, attr_name)
                    if callable(attr):
                        session = attr(server_name)
                    else:
                        session = attr.get(server_name)
                    if session:
                        break
            else:
                raise ValueError(f"MCP session for '{server_name}' not found")
        
        # Call the tool and return the result
        result = await session.call_tool(tool_name, tool_args)
        return result
        
    except Exception as e:
        logger.error(f"Error calling MCP tool '{tool_name}' on server '{server_name}': {e}")
        raise
