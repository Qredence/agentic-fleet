"""
Web Search Agent Module.

This module implements an agent that performs web searches and analyzes
results to provide relevant information for the reasoning process.
"""

from typing import Any, Dict, List, Optional, Sequence

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import ChatMessage
from autogen_core import CancellationToken
from autogen_core.models._model_client import CreateResult, LLMMessage, RequestUsage
from pydantic import BaseModel

from agentic_fleet.core.tools.web_search.web_search_tool import (
    SearchResult,
    WebSearchTool,
)


class WebSearchConfig(BaseModel):
    """Configuration for the Web Search Agent."""

    max_results: int = 5
    min_relevance_score: float = 0.7
    analysis_temperature: float = 0.7
    synthesis_temperature: float = 0.8


class WebSearchAgent(BaseChatAgent):
    """
    Agent that performs web searches and analyzes results to provide
    relevant information for the reasoning process.
    """

    def __init__(
        self,
        name: str = "web_search_agent",
        description: str = "",
        temperature: float = 0.6,
        **kwargs
    ) -> None:
        """
        Initialize the Web Search Agent.

        Args:
            name: Name of the agent
            description: Description of the agent
            temperature: Temperature for the agent
            **kwargs: Additional arguments passed to BaseChatAgent
        """
        super().__init__(name=name, description=description, **kwargs)
        self.temperature = temperature

        # Extract config from kwargs or use defaults
        config = WebSearchConfig(**kwargs.get("config", {}))
        self.web_search_tool = WebSearchTool(
            max_results=config.max_results, min_relevance_score=config.min_relevance_score
        )
        self.config = config

    async def process_message(
        self, message: ChatMessage, token: CancellationToken = None
    ) -> Response:
        """
        Process incoming messages and manage web search operations.

        Args:
            message: Incoming chat message
            token: Cancellation token for the operation

        Returns:
            Response containing the search and analysis results
        """
        try:
            # Parse the command and parameters from the message
            command, params = self._parse_message(message.content)

            if command == "search":
                results = await self._perform_search(
                    params.get("query", ""), params.get("context", {})
                )
                return Response(content=str(results))

            elif command == "analyze":
                analysis = await self._analyze_results(
                    params.get("results", []), params.get("focus", None)
                )
                return Response(content=analysis)

            elif command == "synthesize":
                synthesis = await self._synthesize_information(
                    params.get("query", ""), params.get("context", {})
                )
                return Response(content=synthesis)

            else:
                return Response(
                    content=f"Unknown command: {command}. Available commands: search, analyze, synthesize",
                    error=True
                )

        except Exception as e:
            return Response(content=f"Error processing web search operation: {str(e)}", error=True)

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
        return Response(content=response.result if response else "Failed to process message")

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
        return ["text", "search_results"]

    async def _perform_search(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Perform a web search and return relevant results.

        Args:
            query: Search query
            context: Optional context to refine the search

        Returns:
            List of search results
        """
        try:
            # Refine the query using context if available
            if context:
                refined_query = await self._refine_query(query, context)
            else:
                refined_query = query

            # Perform the search
            results = await self.web_search_tool.search(refined_query)

            # Filter results by relevance
            filtered_results = [
                result
                for result in results
                if result.relevance_score >= self.config.min_relevance_score
            ]

            return filtered_results[: self.config.max_results]

        except Exception as e:
            raise RuntimeError(f"Error performing web search: {str(e)}")

    async def _analyze_results(
        self, results: List[SearchResult], focus: Optional[str] = None
    ) -> str:
        """
        Analyze search results to extract key information.

        Args:
            results: List of search results to analyze
            focus: Optional focus area for analysis

        Returns:
            Analysis of the search results
        """
        try:
            # Create messages for analysis
            messages = [
                LLMMessage(
                    role="system", content="Analyze the search results and extract key information."
                ),
                LLMMessage(role="user", content=f"Results: {results}\nFocus Area: {focus}"),
            ]

            result = await self.generate_response(
                messages, temperature=self.config.analysis_temperature
            )
            return result.message.content

        except Exception as e:
            raise RuntimeError(f"Error analyzing search results: {str(e)}")

    async def _synthesize_information(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Synthesize information from search results into a coherent response.

        Args:
            query: Original search query
            context: Optional context for synthesis

        Returns:
            Synthesized information
        """
        try:
            # Perform search
            results = await self._perform_search(query, context)

            # Analyze results
            analysis = await self._analyze_results(results)

            # Create messages for synthesis
            messages = [
                LLMMessage(
                    role="system",
                    content="Synthesize the analyzed information into a coherent response.",
                ),
                LLMMessage(
                    role="user", content=f"Query: {query}\nAnalysis: {analysis}\nContext: {context}"
                ),
            ]

            result = await self.generate_response(
                messages, temperature=self.config.synthesis_temperature
            )
            return result.message.content

        except Exception as e:
            raise RuntimeError(f"Error synthesizing information: {str(e)}")

    async def _refine_query(self, query: str, context: Dict[str, Any]) -> str:
        """
        Refine a search query using context information.

        Args:
            query: Original search query
            context: Context information for refinement

        Returns:
            Refined search query
        """
        try:
            messages = [
                LLMMessage(
                    role="system", content="Refine the search query using the provided context."
                ),
                LLMMessage(role="user", content=f"Query: {query}\nContext: {context}"),
            ]

            result = await self.generate_response(messages)
            return result.message.content

        except Exception as e:
            raise RuntimeError(f"Error refining query: {str(e)}")

    def _parse_message(self, content: str) -> tuple[str, Dict[str, Any]]:
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
