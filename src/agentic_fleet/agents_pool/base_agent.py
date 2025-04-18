"""Base agent implementation.

This module provides a base agent implementation that can be extended by other agents.
"""

from typing import Any, Dict, List, Optional


class BaseAgent:
    """Base agent implementation."""

    def __init__(self, name: str, description: str = "", **kwargs: Any):
        """Initialize the base agent.
        
        Args:
            name: The name of the agent
            description: A description of the agent
            **kwargs: Additional parameters for the agent
        """
        self.name = name
        self.description = description
        self.kwargs = kwargs
        self.initialized = False
        
    async def initialize(self) -> None:
        """Initialize the agent.
        
        This method should be called before using the agent.
        """
        self.initialized = True
        
    async def process(self, message: str) -> str:
        """Process a message and return a response.
        
        Args:
            message: The message to process
            
        Returns:
            The response from the agent
            
        Raises:
            ValueError: If the agent is not initialized
        """
        if not self.initialized:
            raise ValueError("Agent not initialized")
        
        # Base implementation just returns the message
        return f"[{self.name}] Received: {message}"
        
    async def shutdown(self) -> None:
        """Shut down the agent.
        
        This method should be called when the agent is no longer needed.
        """
        self.initialized = False
