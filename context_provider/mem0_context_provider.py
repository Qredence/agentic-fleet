import os
from mem0 import Memory
from openai import AzureOpenAI
from dotenv import load_dotenv

from config.settings import settings

load_dotenv()


class Mem0ContextProvider:
    """A context provider that uses mem0ai for memory management."""

    def __init__(self):
        """Initialize the Mem0ContextProvider."""
        azure_client = AzureOpenAI(
            azure_endpoint=settings.azure_ai_project_endpoint,
            api_key=settings.openai_api_key,
            api_version="2024-02-01",
        )

        config = {
            "vector_store": {
                "provider": "azure_ai_search",
                "config": {
                    "service_name": settings.azure_ai_search_endpoint,
                    "api_key": settings.azure_ai_search_key,
                    "endpoint": settings.azure_ai_search_endpoint,
                    "collection_name": "agenticfleet-memories",
                },
            },
            "llm": {
                "provider": "azure_openai",
                "config": {
                    "azure_client": azure_client,
                    "model": settings.azure_openai_chat_completion_deployed_model_name,
                    "temperature": 0,
                    "max_tokens": 1000,
                },
            },
            "embedder": {
                "provider": "azure_openai",
                "config": {
                    "azure_client": azure_client,
                    "model": settings.azure_openai_embedding_deployed_model_name,
                },
            },
        }

        self.memory = Memory(config)

    def get(self, query: str) -> str:
        """Get memories for a given query."""
        return self.memory.search(query)

    def add(self, data: str):
        """Add a new memory."""
        self.memory.add(data)
