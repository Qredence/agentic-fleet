"""Base MCP implementation.

This module provides a base MCP (Multi-agent Cognitive Protocol) implementation 
that can be extended by other MCP implementations.
"""

from typing import Any, Dict, List, Optional, Set


class BaseMCP:
    """Base MCP implementation for multi-agent coordination."""

    def __init__(self, name: str, description: str = "", **kwargs: Any):
        """Initialize the base MCP.
        
        Args:
            name: The name of the MCP
            description: A description of the MCP
            **kwargs: Additional parameters for the MCP
        """
        self.name = name
        self.description = description
        self.kwargs = kwargs
        self.agents: Dict[str, Any] = {}
        self.tools: Dict[str, Any] = {}
        self.initialized = False
        
    async def initialize(self) -> None:
        """Initialize the MCP.
        
        This method should be called before using the MCP.
        """
        self.initialized = True
        
    async def register_agent(self, agent_id: str, agent: Any) -> None:
        """Register an agent with the MCP.
        
        Args:
            agent_id: The ID of the agent
            agent: The agent to register
        """
        self.agents[agent_id] = agent
        
    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the MCP.
        
        Args:
            agent_id: The ID of the agent to unregister
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            
    async def register_tool(self, tool_id: str, tool: Any) -> None:
        """Register a tool with the MCP.
        
        Args:
            tool_id: The ID of the tool
            tool: The tool to register
        """
        self.tools[tool_id] = tool
        
    async def unregister_tool(self, tool_id: str) -> None:
        """Unregister a tool from the MCP.
        
        Args:
            tool_id: The ID of the tool to unregister
        """
        if tool_id in self.tools:
            del self.tools[tool_id]
            
    async def process_message(self, sender_id: str, message: str, recipients: Optional[List[str]] = None) -> Dict[str, Any]:
        """Process a message from an agent and route it to the appropriate recipients.
        
        Args:
            sender_id: The ID of the agent sending the message
            message: The message to process
            recipients: Optional list of recipient agent IDs. If None, the message is broadcast to all agents.
            
        Returns:
            A dictionary containing the results of processing the message
            
        Raises:
            ValueError: If the MCP is not initialized
        """
        if not self.initialized:
            raise ValueError("MCP not initialized")
        
        if sender_id not in self.agents:
            raise ValueError(f"Unknown sender: {sender_id}")
        
        # Determine recipients
        if recipients is None:
            # Broadcast to all agents except the sender
            target_agents = set(self.agents.keys()) - {sender_id}
        else:
            # Send to specified recipients
            target_agents = set(recipients) & set(self.agents.keys())
            
        # Process the message
        results = {}
        for agent_id in target_agents:
            agent = self.agents[agent_id]
            try:
                # This is a simplified implementation
                # In a real implementation, this would use the agent's process method
                results[agent_id] = f"Processed message from {sender_id} to {agent_id}: {message}"
            except Exception as e:
                results[agent_id] = f"Error processing message: {str(e)}"
                
        return {
            "sender": sender_id,
            "message": message,
            "recipients": list(target_agents),
            "results": results
        }
        
    async def shutdown(self) -> None:
        """Shut down the MCP.
        
        This method should be called when the MCP is no longer needed.
        """
        self.initialized = False
        self.agents.clear()
        self.tools.clear()
