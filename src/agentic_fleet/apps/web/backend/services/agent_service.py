"""
Agent service module for managing agent lifecycle and interactions.

This module provides the core service layer for managing agents, including
initialization, message processing, and state management.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from autogen_agentchat.agents._assistant_agent import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

@dataclass
class AgentConfig:
    """Configuration for an agent instance."""
    name: str
    capabilities: List[str]
    parameters: Dict[str, Any]

class AgentService:
    """Service class for managing agent interactions."""

    def __init__(self):
        """Initialize the agent service with default configurations."""
        self._agents: Dict[str, AssistantAgent] = {}
        self._agent_configs: Dict[str, AgentConfig] = self._initialize_configs()
        self._model_client = OpenAIChatCompletionClient(
            config_list=[{"model": "gpt-4"}],
            temperature=0.7
        )

    def _initialize_configs(self) -> Dict[str, AgentConfig]:
        """Initialize default agent configurations."""
        return {
            "coding_agent": AgentConfig(
                name="CodingAgent",
                capabilities=[
                    "Code generation",
                    "Code review",
                    "Debugging",
                    "Refactoring",
                ],
                parameters={},
            ),
            "web_search_agent": AgentConfig(
                name="WebSearchAgent",
                capabilities=[
                    "Web search",
                    "Content analysis",
                    "Information synthesis",
                    "Source validation",
                ],
                parameters={},
            ),
            "mind_map_agent": AgentConfig(
                name="MindMapAgent",
                capabilities=[
                    "Knowledge graph creation",
                    "Relationship analysis",
                    "Topic clustering",
                    "Pattern recognition",
                ],
                parameters={},
            ),
        }

    async def initialize_agents(self) -> None:
        """
        Initialize the agent pool with configured agents.

        This method sets up each agent with its specific configuration
        and ensures all necessary capabilities are available.
        """
        self._agents = {
            "coding_agent": AssistantAgent(
                name=self._agent_configs["coding_agent"].name,
                model_client=self._model_client,
                system_message="I am a coding assistant specialized in multiple languages.",
                description="A coding agent that helps with programming tasks."
            ),
            "web_search_agent": AssistantAgent(
                name=self._agent_configs["web_search_agent"].name,
                model_client=self._model_client,
                system_message="I help with web searches and information synthesis.",
                description="A web search agent that helps find information online."
            ),
            "mind_map_agent": AssistantAgent(
                name=self._agent_configs["mind_map_agent"].name,
                model_client=self._model_client,
                system_message="I create and analyze knowledge graphs.",
                description="A mind map agent that helps organize information."
            ),
        }

    async def process_message(
        self,
        message: str,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a message using the specified agent.

        Args:
            message: The message content to process
            agent_name: Optional name of the agent to use
            metadata: Optional metadata for message processing

        Returns:
            Dict containing the processed response and metadata

        Raises:
            ValueError: If specified agent not found
        """
        if agent_name and agent_name not in self._agents:
            raise ValueError(f"Agent {agent_name} not found")

        agent = self._agents.get(agent_name, self._agents["coding_agent"])

        try:
            # Create message object
            msg = TextMessage(content=message, role="user", metadata=metadata or {})

            # Process message through the agent
            response = await agent.on_messages([msg])

            return {
                "sender": agent_name,
                "content": response.chat_message.content if response and response.chat_message else "No response generated",
                "error": False,
            }

        except Exception as e:
            return {
                "sender": "system",
                "content": f"Error processing message: {str(e)}",
                "error": True,
            }

    def get_agent_info(self, agent_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Dict containing agent configuration and capabilities

        Raises:
            ValueError: If agent not found
        """
        if agent_name not in self._agent_configs:
            raise ValueError(f"Agent {agent_name} not found")

        config = self._agent_configs[agent_name]
        return {
            "name": config.name,
            "description": "",
            "capabilities": config.capabilities,
            "parameters": config.parameters,
        }

    def get_available_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of available agents with their configurations.

        Returns:
            List of agent configurations
        """
        return [self.get_agent_info(name) for name in self._agent_configs.keys()]

    async def update_agent_config(
        self, agent_name: str, new_config: Dict[str, Any]
    ) -> None:
        """
        Update an agent's configuration.

        Args:
            agent_name: Name of the agent to update
            new_config: New configuration parameters

        Raises:
            ValueError: If agent not found
        """
        if agent_name not in self._agent_configs:
            raise ValueError(f"Agent {agent_name} not found")

        # Update configuration
        config = self._agent_configs[agent_name]
        config.parameters.update(new_config)

        # Reinitialize agent with new config
        await self.initialize_agents()
