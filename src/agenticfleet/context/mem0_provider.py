from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from mem0 import Memory  # type: ignore
from mem0.configs.base import (  # type: ignore[import-untyped]
    EmbedderConfig,
    LlmConfig,
    MemoryConfig,
)

from ..config.settings import settings

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
        # Store identifiers for memory operations
        self.user_id = user_id
        self.agent_id = agent_id

        api_key = settings.require_openai_api_key()

        # Configure Mem0 to use OpenAI for both LLM responses and embeddings
        llm_config = LlmConfig(
            provider="openai",
            config={
                "api_key": api_key,
                "model": settings.openai_model,
                "temperature": 0,
                "max_tokens": 1000,
            },
        )
        embedder_config = EmbedderConfig(
            provider="openai",
            config={
                "api_key": api_key,
                "model": settings.openai_embedding_model,
            },
        )

        history_db_path = Path(settings.mem0_history_db_path).resolve()
        history_db_path.parent.mkdir(parents=True, exist_ok=True)

        mem0_config = MemoryConfig(
            llm=llm_config,
            embedder=embedder_config,
            history_db_path=str(history_db_path),
        )

        # Initialize memory with the configured providers
        self.memory = Memory(config=mem0_config)

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
    ) -> None:
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
