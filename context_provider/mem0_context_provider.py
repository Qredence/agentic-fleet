from dotenv import load_dotenv
from mem0 import Memory
from openai import AzureOpenAI

from config.settings import settings

load_dotenv()


class Mem0ContextProvider:
    """A context provider that uses mem0ai for memory management."""

    def __init__(self, user_id: str = "agenticfleet_user", agent_id: str = "orchestrator"):
        """
        Initialize the Mem0ContextProvider.

        Args:
            user_id: Default user identifier for memory operations
            agent_id: Default agent identifier for memory operations
        """
        if settings.azure_ai_project_endpoint is None:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT is required but not set in settings.")

        if settings.azure_ai_search_endpoint is None:
            raise ValueError("AZURE_AI_SEARCH_ENDPOINT is required but not set in settings.")

        if settings.azure_ai_search_key is None:
            raise ValueError("AZURE_AI_SEARCH_KEY is required but not set in settings.")

        # Store identifiers for memory operations
        self.user_id = user_id
        self.agent_id = agent_id

        azure_client = AzureOpenAI(
            azure_endpoint=settings.azure_ai_project_endpoint,
            api_key=settings.openai_api_key,
            api_version="2024-02-01",
        )

        # Extract service name from endpoint if it's a full URL
        service_name = settings.azure_ai_search_endpoint
        if service_name.startswith("https://"):
            # Extract service name from URL like https://myservice.search.windows.net
            service_name = service_name.replace("https://", "").split(".")[0]

        config = {
            "vector_store": {
                "provider": "azure_ai_search",
                "config": {
                    "service_name": service_name,
                    "api_key": settings.azure_ai_search_key,
                    "collection_name": "agenticfleet-memories",
                    "embedding_model_dims": 1536,
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

        # Initialize memory using from_config method
        self.memory = Memory.from_config(config)

    def get(self, query: str, user_id: str | None = None, agent_id: str | None = None) -> str:
        """
        Get memories for a given query.

        Args:
            query: The search query
            user_id: Optional user identifier (uses default if not provided)
            agent_id: Optional agent identifier (uses default if not provided)

        Returns:
            Concatenated memory strings
        """
        # Use provided IDs or fall back to defaults
        uid = user_id or self.user_id
        aid = agent_id or self.agent_id

        try:
            results = self.memory.search(query, user_id=uid, agent_id=aid)

            # Extract memory text from results
            # Results format: [{"memory": "text", "score": 0.95, ...}, ...]
            memories = []
            if isinstance(results, list):
                for result in results:
                    if isinstance(result, dict):
                        memory_text = result.get("memory", "")
                        if memory_text:
                            memories.append(str(memory_text))

            return "\n".join(memories) if memories else ""
        except Exception as e:
            # Log error and return empty string to avoid breaking the workflow
            print(f"Error searching memories: {e}")
            return ""

    def add(
        self,
        data: str,
        user_id: str | None = None,
        agent_id: str | None = None,
        metadata: dict | None = None,
    ):
        """
        Add a new memory.

        Args:
            data: The memory content to add
            user_id: Optional user identifier (uses default if not provided)
            agent_id: Optional agent identifier (uses default if not provided)
            metadata: Optional metadata to associate with the memory
        """
        # Use provided IDs or fall back to defaults
        uid = user_id or self.user_id
        aid = agent_id or self.agent_id

        try:
            self.memory.add(data, user_id=uid, agent_id=aid, metadata=metadata or {})
        except Exception as e:
            # Log error but don't raise to avoid breaking the workflow
            print(f"Error adding memory: {e}")
