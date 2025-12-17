"""Azure AI Search Context Provider."""

import logging
import os
from collections.abc import MutableSequence
from typing import Any

from agent_framework._memory import Context, ContextProvider
from agent_framework._types import ChatMessage
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

logger = logging.getLogger(__name__)


class AzureAISearchContextProvider(ContextProvider):
    """
    Context provider that retrieves relevant documents from Azure AI Search.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        index_name: str | None = None,
        api_key: str | None = None,
        top: int = 3,
        semantic_configuration_name: str | None = None,
    ) -> None:
        """
        Initialize the Azure AI Search context provider.

        Args:
            endpoint: The endpoint URL of the Azure AI Search service.
            index_name: The name of the index to search.
            api_key: The API key for the Azure AI Search service.
            top: The number of results to retrieve.
            semantic_configuration_name: The name of the semantic configuration to use (optional).
        """
        self.endpoint = endpoint or os.getenv("AZURE_SEARCH_ENDPOINT")
        self.index_name = index_name or os.getenv("AZURE_SEARCH_INDEX")
        self.api_key = api_key or os.getenv("AZURE_SEARCH_KEY")
        self.top = top
        self.semantic_configuration_name = semantic_configuration_name

        if not self.endpoint or not self.index_name or not self.api_key:
            logger.warning(
                "Azure AI Search credentials not fully configured. "
                "AzureAISearchContextProvider will be disabled."
            )
            self._client = None
        else:
            try:
                self._client = SearchClient(
                    endpoint=self.endpoint,
                    index_name=self.index_name,
                    credential=AzureKeyCredential(self.api_key),
                )
            except Exception as e:
                logger.error("Failed to initialize Azure AI Search client: %s", e)
                self._client = None

    async def invoking(
        self, messages: ChatMessage | MutableSequence[ChatMessage], **kwargs: Any
    ) -> Context:
        """
        Retrieve context from Azure AI Search based on the last message.

        Args:
            messages: The chat messages.
            **kwargs: Additional arguments.

        Returns:
            Context: The context containing the retrieved documents.
        """
        if not self._client:
            return Context()

        query = self._extract_query(messages)
        if not query:
            return Context()

        try:
            # Use semantic search if configuration is provided, otherwise simple search
            if self.semantic_configuration_name:
                results = self._client.search(
                    search_text=query,
                    top=self.top,
                    query_type="semantic",
                    semantic_configuration_name=self.semantic_configuration_name,
                )
            else:
                results = self._client.search(search_text=query, top=self.top)

            context_text = self._format_results(results)
            if not context_text:
                return Context()

            return Context(
                instructions=f"Use the following information from the knowledge base to answer the user's request:\n\n{context_text}"
            )

        except Exception as e:
            logger.error("Error querying Azure AI Search: %s", e)
            return Context()

    def _extract_query(self, messages: ChatMessage | MutableSequence[ChatMessage]) -> str | None:
        """Extract the query from the last user message."""
        if isinstance(messages, ChatMessage):
            return messages.text

        if not messages:
            return None

        # Get the last message
        last_message = messages[-1]
        return last_message.text

    def _format_results(self, results: Any) -> str:
        """Format the search results into a string."""
        formatted_results = []
        for result in results:
            # Try to find content fields
            content = result.get("content") or result.get("text") or result.get("description")
            source = (
                result.get("source") or result.get("url") or result.get("title") or "Unknown Source"
            )

            if content:
                formatted_results.append(f"Source: {source}\nContent: {content}")

        return "\n\n".join(formatted_results)
