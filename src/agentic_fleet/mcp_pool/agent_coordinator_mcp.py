"""Agent Coordinator MCP implementation.

This module provides an MCP implementation for coordinating multiple agents.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from agentic_fleet.mcp_pool.base_mcp import BaseMCP

logger = logging.getLogger(__name__)


class AgentCoordinatorMCP(BaseMCP):
    """MCP implementation for coordinating multiple agents."""

    def __init__(
        self, 
        name: str = "agent_coordinator", 
        description: str = "Coordinates multiple agents", 
        **kwargs: Any
    ):
        """Initialize the agent coordinator MCP.
        
        Args:
            name: The name of the MCP
            description: A description of the MCP
            **kwargs: Additional parameters for the MCP
        """
        super().__init__(name, description, **kwargs)
        self.conversation_history: List[Dict[str, Any]] = []
        self.agent_capabilities: Dict[str, List[str]] = {}
        
    async def register_agent(self, agent_id: str, agent: Any, capabilities: Optional[List[str]] = None) -> None:
        """Register an agent with the MCP and its capabilities.
        
        Args:
            agent_id: The ID of the agent
            agent: The agent to register
            capabilities: Optional list of capabilities the agent has
        """
        await super().register_agent(agent_id, agent)
        self.agent_capabilities[agent_id] = capabilities or []
        logger.info(f"Registered agent {agent_id} with capabilities: {capabilities}")
        
    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the MCP.
        
        Args:
            agent_id: The ID of the agent to unregister
        """
        await super().unregister_agent(agent_id)
        if agent_id in self.agent_capabilities:
            del self.agent_capabilities[agent_id]
        logger.info(f"Unregistered agent {agent_id}")
        
    async def find_agents_with_capability(self, capability: str) -> List[str]:
        """Find agents with a specific capability.
        
        Args:
            capability: The capability to search for
            
        Returns:
            A list of agent IDs that have the specified capability
        """
        return [
            agent_id 
            for agent_id, capabilities in self.agent_capabilities.items() 
            if capability in capabilities
        ]
        
    async def process_message(
        self, 
        sender_id: str, 
        message: str, 
        recipients: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a message from an agent and route it to the appropriate recipients.
        
        Args:
            sender_id: The ID of the agent sending the message
            message: The message to process
            recipients: Optional list of recipient agent IDs. If None, the message is broadcast to all agents.
            metadata: Optional metadata to include with the message
            
        Returns:
            A dictionary containing the results of processing the message
        """
        if not self.initialized:
            raise ValueError("MCP not initialized")
        
        if sender_id not in self.agents:
            raise ValueError(f"Unknown sender: {sender_id}")
        
        # Record the message in the conversation history
        message_entry = {
            "sender": sender_id,
            "message": message,
            "recipients": recipients,
            "metadata": metadata or {},
            "timestamp": self.kwargs.get("get_timestamp", lambda: None)()
        }
        self.conversation_history.append(message_entry)
        
        # Process the message using the base implementation
        result = await super().process_message(sender_id, message, recipients)
        
        # Add the result to the conversation history
        self.conversation_history.append({
            "type": "result",
            "data": result,
            "timestamp": self.kwargs.get("get_timestamp", lambda: None)()
        })
        
        return result
        
    async def get_conversation_history(
        self, 
        limit: Optional[int] = None, 
        agent_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get the conversation history.
        
        Args:
            limit: Optional limit on the number of messages to return
            agent_filter: Optional filter to only include messages from a specific agent
            
        Returns:
            A list of message entries from the conversation history
        """
        if agent_filter:
            filtered_history = [
                entry for entry in self.conversation_history
                if entry.get("type") != "result" and (
                    entry.get("sender") == agent_filter or 
                    (entry.get("recipients") and agent_filter in entry.get("recipients", []))
                )
            ]
        else:
            filtered_history = self.conversation_history
            
        if limit:
            return filtered_history[-limit:]
        return filtered_history
        
    async def clear_conversation_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history.clear()
        logger.info("Cleared conversation history")
        
    async def shutdown(self) -> None:
        """Shut down the MCP."""
        await super().shutdown()
        self.conversation_history.clear()
        self.agent_capabilities.clear()
