"""LLM-based agent implementation.

This module provides an agent implementation that uses an LLM for processing.
"""

from typing import Any, Dict, List, Optional

from agentic_fleet.agents_pool.base_agent import BaseAgent
from agentic_fleet.services.client_factory import get_cached_client


class LLMAgent(BaseAgent):
    """LLM-based agent implementation."""

    def __init__(
        self,
        name: str,
        model_name: str,
        description: str = "",
        streaming: bool = True,
        **kwargs: Any
    ):
        """Initialize the LLM agent.
        
        Args:
            name: The name of the agent
            model_name: The name of the LLM model to use
            description: A description of the agent
            streaming: Whether to enable streaming responses
            **kwargs: Additional parameters for the agent
        """
        super().__init__(name, description, **kwargs)
        self.model_name = model_name
        self.streaming = streaming
        self.client = None
        
    async def initialize(self) -> None:
        """Initialize the agent.
        
        This method creates the LLM client.
        """
        # Create the LLM client
        self.client = get_cached_client(
            model_name=self.model_name,
            streaming=self.streaming,
            **self.kwargs
        )
        
        await super().initialize()
        
    async def process(self, message: str) -> str:
        """Process a message using the LLM and return a response.
        
        Args:
            message: The message to process
            
        Returns:
            The response from the LLM
            
        Raises:
            ValueError: If the agent is not initialized
        """
        if not self.initialized:
            raise ValueError("Agent not initialized")
        
        if not self.client:
            raise ValueError("LLM client not initialized")
        
        # Process the message using the LLM client
        # This is a simplified implementation
        return f"[{self.name}] LLM response to: {message}"
        
    async def shutdown(self) -> None:
        """Shut down the agent.
        
        This method cleans up the LLM client.
        """
        self.client = None
        await super().shutdown()
