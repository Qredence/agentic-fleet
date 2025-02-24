"""
Mind Map Agent Module.

This module implements an agent that constructs and analyzes knowledge graphs
to track logical relationships in complex reasoning chains.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import ChatMessage
from autogen_core import CancellationToken
from autogen_core.models._model_client import CreateResult, LLMMessage, RequestUsage
from pydantic import BaseModel

from agentic_fleet.core.tools.mind_map.mind_map_tool import (
    MindMapTool,
)


class MindMapConfig(BaseModel):
    """Configuration for the Mind Map Agent."""

    graph_type: str = "directed"
    max_nodes: int = 50
    clustering_threshold: float = 0.7
    entity_extraction_temperature: float = 0.7
    relationship_extraction_temperature: float = 0.8


class MindMapAgent(BaseChatAgent):
    """
    Agent that constructs and analyzes knowledge graphs to track
    logical relationships in complex reasoning chains.
    """

    def __init__(
        self,
        name: str = "mind_map_agent",
        description: str = "",
        temperature: float = 0.5,
        **kwargs: Any
    ) -> None:
        """
        Initialize the Mind Map Agent.

        Args:
            name: Name of the agent
            description: Description of the agent
            temperature: Temperature parameter for entity and relationship extraction
            **kwargs: Additional arguments passed to BaseChatAgent
        """
        super().__init__(name=name, description=description, **kwargs)

        # Extract config from kwargs or use defaults
        config = MindMapConfig(**kwargs.get("config", {}))
        self.mind_map_tool = MindMapTool(
            graph_type=config.graph_type,
            max_nodes=config.max_nodes,
            clustering_threshold=config.clustering_threshold,
        )
        self.config = config
        self.temperature = temperature

    async def process_message(
        self, message: ChatMessage, token: CancellationToken = None
    ) -> Response:
        """
        Process incoming messages and manage the mind map operations.

        Args:
            message: Incoming chat message
            token: Cancellation token for the operation

        Returns:
            Response containing the operation result
        """
        try:
            # Parse the command and parameters from the message
            command, params = self._parse_message(message.content)

            if command == "construct":
                result = await self._construct_mind_map(
                    params.get("reasoning_chain", ""), params.get("context", {})
                )
                return Response(content=str(result))

            elif command == "insights":
                insights = await self._extract_insights(params.get("focus_area"))
                return Response(content=insights)

            elif command == "recommendations":
                recommendations = await self._get_recommendations(
                    params.get("query", ""), params.get("context", {})
                )
                return Response(content=str(recommendations))

            elif command == "clear":
                self.mind_map_tool.clear_graph()
                return Response(content="Mind map cleared successfully")

            else:
                return Response(
                    content=f"Unknown command: {command}. Available commands: construct, insights, recommendations, clear"
                )

        except Exception as e:
            return Response(content=f"Error processing mind map operation: {str(e)}", error=True)

    async def generate_response(
        self, messages: Sequence[LLMMessage], token: CancellationToken = None
    ) -> CreateResult:
        """
        Generate a response based on the message history.

        Args:
            messages: Sequence of messages in the conversation
            token: Cancellation token for the operation

        Returns:
            CreateResult containing the generated response
        """
        result = await super().generate_response(messages, token)

        # Add token usage information
        if not hasattr(result, "usage"):
            result.usage = RequestUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)

        return result

    async def _construct_mind_map(
        self, reasoning_chain: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Construct a mind map from a reasoning chain.

        Args:
            reasoning_chain: Text containing the reasoning process
            context: Optional context information

        Returns:
            Dictionary containing the constructed mind map
        """
        try:
            # Extract entities
            entities_data = await self._extract_entities(
                reasoning_chain, self.temperature
            )
            self.mind_map_tool.add_entities(entities_data)

            # Extract relationships
            relationships_data = await self._extract_relationships(
                reasoning_chain, self.temperature
            )
            self.mind_map_tool.add_relationships(relationships_data)

            return self.mind_map_tool.get_graph_state()

        except Exception as e:
            raise RuntimeError(f"Error constructing mind map: {str(e)}")

    async def _extract_insights(self, focus_area: Optional[str] = None) -> str:
        """
        Extract insights from the current mind map.

        Args:
            focus_area: Optional area to focus analysis on

        Returns:
            String containing extracted insights
        """
        try:
            analysis = self.mind_map_tool.analyze_graph()
            messages = [
                LLMMessage(role="system", content="Extract key insights from the graph analysis."),
                LLMMessage(role="user", content=f"Analysis: {analysis}\nFocus Area: {focus_area}"),
            ]
            result = await self.generate_response(messages)
            return result.message.content

        except Exception as e:
            raise RuntimeError(f"Error extracting insights: {str(e)}")

    async def _get_recommendations(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get strategic recommendations based on the mind map.

        Args:
            query: Query to focus recommendations on
            context: Optional context information

        Returns:
            List of recommendation objects
        """
        try:
            graph_state = self.mind_map_tool.get_graph_state()
            messages = [
                LLMMessage(
                    role="system",
                    content="Generate strategic recommendations based on the mind map.",
                ),
                LLMMessage(
                    role="user",
                    content=f"Query: {query}\nGraph State: {graph_state}\nContext: {context}",
                ),
            ]
            result = await self.generate_response(messages)
            return self._parse_recommendations(result.message.content)

        except Exception as e:
            raise RuntimeError(f"Error generating recommendations: {str(e)}")

    def _parse_message(self, content: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse the command and parameters from a message.

        Args:
            content: Message content to parse

        Returns:
            Tuple of (command, parameters)
        """
        # Simple parsing - could be enhanced based on needs
        parts = content.split(maxsplit=1)
        command = parts[0].lower()
        params = {}

        if len(parts) > 1:
            # Parse parameters from the rest of the message
            param_text = parts[1]
            try:
                import json

                params = json.loads(param_text)
            except json.JSONDecodeError:
                params = {"content": param_text}

        return command, params

    async def _extract_entities(self, text: str, temperature: float) -> str:
        """Extract entities from text using LLM."""
        messages = [
            LLMMessage(
                role="system", content="Extract key entities from the text. Format as JSON."
            ),
            LLMMessage(role="user", content=text),
        ]
        result = await self.generate_response(messages)
        return result.message.content

    async def _extract_relationships(self, text: str, temperature: float) -> str:
        """Extract relationships from text using LLM."""
        messages = [
            LLMMessage(
                role="system", content="Extract relationships between entities. Format as JSON."
            ),
            LLMMessage(role="user", content=text),
        ]
        result = await self.generate_response(messages)
        return result.message.content

    def _parse_recommendations(self, text: str) -> List[Dict[str, Any]]:
        """Parse recommendations from LLM response."""
        try:
            import json

            return json.loads(text)
        except json.JSONDecodeError:
            return [{"error": "Failed to parse recommendations"}]

    async def on_messages(self, messages: Sequence[ChatMessage]) -> Response:
        """
        Handle incoming messages and generate responses.

        Args:
            messages: Sequence of messages to process

        Returns:
            Response: The agent's response to the messages
        """
        if not messages:
            return Response(content="No messages to process")

        # For now, just process the last message
        last_message = messages[-1]
        response = await self.process_message(last_message)
        return Response(content=response if response else "Failed to process message")

    async def on_reset(self) -> None:
        """Reset the agent's state."""
        # No state to reset for now
        pass

    def produced_message_types(self) -> List[str]:
        """
        Get the types of messages this agent can produce.

        Returns:
            List[str]: List of supported message types
        """
        return ["text", "mind_map"]
