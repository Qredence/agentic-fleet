"""
Base Agent Module.

This module defines the base agent class that all specialized agents
(Mind Map Agent, Web Search Agent, Coding Agent) will inherit from.
It follows the patterns from the latest Microsoft Autogen documentation.
"""

from typing import Any, Dict, List, Optional, Union

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import ChatMessage, TextMessage
from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient

from ..config.configuration_manager import AgentConfig


class BaseAgent(AssistantAgent):
    """
    Base class for all agents in the Agentic Reasoning System.

    This class extends AssistantAgent from autogen-core and provides
    common functionality for all specialized agents in the system.
    """

    component_type = "agent"
    version = 1

    def __init__(
        self,
        name: str,
        model_client: Optional[ChatCompletionClient] = None,
        description: Optional[str] = None,
        system_message: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a new agent instance.

        Args:
            name: The name of this agent instance.
            model_client: The model client to use for this agent.
            description: Description of the agent's purpose.
            system_message: Optional system message to configure the agent's behavior.
            **kwargs: Additional keyword arguments for specialized agent configuration.
        """
        super().__init__(
            name=name,
            system_message=system_message or self._get_default_system_message(),
            model_client=model_client,
            description=description or self._get_default_description(),
            **kwargs,
        )
        self._initialize_agent(**kwargs)

    def _get_default_system_message(self) -> str:
        """Get the default system message for this agent type."""
        return f"You are {self.name}, a helpful AI assistant."

    def _get_default_description(self) -> str:
        """Get the default description for this agent type."""
        return "An agent that provides assistance with ability to use tools."

    def _initialize_agent(self, **kwargs: Any) -> None:
        """
        Perform any additional initialization specific to this agent type.
        Can be overridden by specialized agents.
        """
        pass

    async def process_message(self, message: Union[str, ChatMessage]) -> Dict[str, Any]:
        """
        Process an incoming message and generate a response.

        Args:
            message: The input message to process.

        Returns:
            A dictionary containing the agent's response and any additional data.
        """
        if isinstance(message, str):
            message = TextMessage(content=message, source="user")

        response = await self.generate_response(messages=[message])
        return {"content": response.content, "role": "assistant", "metadata": response.model_dump()}

    async def run(self, task: Union[str, List[ChatMessage]]) -> Dict[str, Any]:
        """
        Execute the agent's primary task.

        Args:
            task: The task description or list of messages to process.

        Returns:
            A dictionary containing the task results and any additional data.
        """
        if isinstance(task, str):
            task = [TextMessage(content=task, source="user")]

        response = await self.generate_response(messages=task)
        return {"content": response.content, "role": "assistant", "metadata": response.model_dump()}

    def dump_component(self) -> Dict[str, Any]:
        """
        Dump the agent configuration to a dictionary format.

        Returns:
            A dictionary containing the agent's configuration.
        """
        config = AgentConfig(
            name=self.name,
            description=self.description,
            system_message=self.system_message,
            model=getattr(self.model_client, "model", None),
        )

        return {
            "provider": f"{self.__class__.__module__}.{self.__class__.__name__}",
            "component_type": self.component_type,
            "version": self.version,
            "component_version": 1,
            "description": self.description,
            "label": self.__class__.__name__,
            "config": config.model_dump(),
        }

    @classmethod
    def load_component(cls, config: Dict[str, Any]) -> "BaseAgent":
        """
        Load an agent from a configuration dictionary.

        Args:
            config: Configuration dictionary from dump_component.

        Returns:
            An instance of the agent.
        """
        agent_config = AgentConfig(**config["config"])
        return cls(
            name=agent_config.name,
            description=agent_config.description,
            system_message=agent_config.system_message,
        )
