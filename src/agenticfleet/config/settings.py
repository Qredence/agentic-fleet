"""Config settings management for AgenticFleet."""

import importlib.util
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import yaml
from agent_framework import CheckpointStorage, InMemoryCheckpointStorage
from dotenv import load_dotenv

from agenticfleet.core.checkpoints import AgenticFleetFileCheckpointStorage
from agenticfleet.core.exceptions import AgentConfigurationError
from agenticfleet.core.logging import setup_logging

load_dotenv()


class Settings:
    """Application settings with environment variable support."""

    def __init__(self) -> None:
        """Initialize settings from environment variables and config files."""
        # Required environment variables (validated lazily when accessed)
        self._openai_api_key = os.getenv("OPENAI_API_KEY")

        # Azure AI Project endpoint (optional - required only for certain features like Mem0)
        self.azure_ai_project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

        # Optional environment variables with defaults
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self.openai_embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_file = os.getenv("LOG_FILE", "var/logs/agenticfleet.log")
        self.log_file = self._rewrite_runtime_path(
            self.log_file,
            env_var_name="LOG_FILE",
            old_prefix="logs",
            new_prefix="var/logs",
        )

        # LiteLLM configuration (optional - for universal LLM proxy support)
        self.use_litellm = os.getenv("USE_LITELLM", "false").lower() == "true"
        self.litellm_model = os.getenv(
            "LITELLM_MODEL"
        )  # e.g., "gpt-4o-mini" or "anthropic/claude-3-5-sonnet-20241022"
        self.litellm_api_key = os.getenv(
            "LITELLM_API_KEY"
        )  # Optional, can use provider-specific keys
        self.litellm_base_url = os.getenv("LITELLM_BASE_URL")  # Optional, for custom endpoints
        self.litellm_timeout = float(os.getenv("LITELLM_TIMEOUT", "600"))  # Default 10 minutes

        # Mem0 configuration
        self.mem0_history_db_path = os.getenv("MEM0_HISTORY_DB_PATH", "var/memories/history.db")
        self.mem0_history_db_path = self._rewrite_runtime_path(
            self.mem0_history_db_path,
            env_var_name="MEM0_HISTORY_DB_PATH",
            old_prefix="memories",
            new_prefix="var/memories",
        )

        # Ensure parent directory for history DB exists when using the default path
        history_path = Path(self.mem0_history_db_path)
        history_path.parent.mkdir(parents=True, exist_ok=True)

        # Redis configuration (optional)
        self.redis_url = os.getenv("REDIS_URL")

        # Azure-specific settings
        self.azure_ai_search_endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
        self.azure_ai_search_key = os.getenv("AZURE_AI_SEARCH_KEY")
        self.azure_openai_chat_completion_deployed_model_name = os.getenv(
            "AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME"
        )
        self.azure_openai_embedding_deployed_model_name = os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME"
        )

        # Observability settings
        self.enable_otel = os.getenv("ENABLE_OTEL", "true").lower() == "true"
        self.enable_sensitive_data = os.getenv("ENABLE_SENSITIVE_DATA", "false").lower() == "true"
        self.otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")

        # Setup logging
        setup_logging(level=self.log_level, log_file=self.log_file)

        # Load workflow configuration
        self.workflow_config = self._load_yaml(self._get_config_path("workflow.yaml"))

    def _get_config_path(self, filename: str) -> Path:
        """
        Get the full path to a config file.

        Args:
            filename: Name of the config file

        Returns:
            Path to the config file
        """
        # Config files are in src/agenticfleet/config/
        return Path(__file__).parent / filename

    def _load_yaml(self, file_path: Path | str) -> dict[str, Any]:
        """
        Load YAML configuration file.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed YAML content as dictionary
        """
        try:
            with open(file_path) as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logging.warning(f"Configuration file not found: {file_path}")
            return {}
        except yaml.YAMLError as e:
            raise AgentConfigurationError(f"Failed to parse YAML file {file_path}: {e}") from e

    def load_agent_config(self, agent_name: str) -> dict[str, Any]:
        """
        Load agent-specific configuration from its directory.

        Args:
            agent_name: Name of the agent (e.g., 'orchestrator', 'researcher')

        Returns:
            Dict containing agent configuration
        """
        # Agent configs are in src/agenticfleet/agents/<agent_name>/config.yaml
        agents_path = Path(__file__).parent.parent / "agents"
        config_path = agents_path / agent_name / "config.yaml"

        return self._load_yaml(config_path)

    def create_checkpoint_storage(self) -> CheckpointStorage | None:
        """
        Create checkpoint storage based on workflow configuration.

        Returns:
            CheckpointStorage instance or None if checkpointing is disabled
        """
        workflow_config = self.workflow_config.get("workflow", {})
        checkpoint_config = workflow_config.get("checkpointing", {})

        if not checkpoint_config.get("enabled", False):
            return None

        storage_type = checkpoint_config.get("storage_type", "file")

        if storage_type == "memory":
            storage_cls = cast(Any, InMemoryCheckpointStorage)
            if storage_cls is None:
                logging.warning("InMemoryCheckpointStorage not available")
                return None
            return storage_cls()  # type: ignore[no-any-return]
        elif storage_type == "file":
            storage_path = checkpoint_config.get("storage_path", "./var/checkpoints")
            storage_path = self._rewrite_runtime_path(
                storage_path,
                env_var_name=None,
                old_prefix="checkpoints",
                new_prefix="var/checkpoints",
            )
            # Ensure the checkpoints directory exists
            Path(storage_path).mkdir(parents=True, exist_ok=True)
            # AgenticFleetFileCheckpointStorage extends FileCheckpointStorage but overrides
            # list_checkpoints signature for our use case - cast to satisfy type checker
            return cast(CheckpointStorage, AgenticFleetFileCheckpointStorage(storage_path))
        else:
            logging.warning(
                f"Unknown checkpoint storage type: {storage_type}. Checkpointing disabled."
            )
            return None

    def redis_chat_message_store_factory(
        self,
        *,
        key_prefix: str | None = None,
        max_messages: int | None = None,
    ) -> Callable[[], Any] | None:
        """Return a factory for Redis-backed chat message stores, if available."""

        try:
            redis_spec = importlib.util.find_spec("agent_framework_redis")
        except (ModuleNotFoundError, ImportError):
            redis_spec = None
        if not (redis_spec and self.redis_url):
            return None

        from agent_framework_redis import RedisChatMessageStore  # type: ignore[import-untyped]

        config_source = self.workflow_config.get("redis", {}).get("chat_store", {})
        allowed_keys = {"key_prefix", "max_messages"}

        factory_kwargs: dict[str, Any] = {
            key: config_source[key] for key in allowed_keys if key in config_source
        }

        if key_prefix is not None:
            factory_kwargs["key_prefix"] = key_prefix
        if max_messages is not None:
            factory_kwargs["max_messages"] = max_messages

        def factory() -> Any:
            return RedisChatMessageStore(redis_url=self.redis_url, **factory_kwargs)

        return factory

    def create_redis_provider(
        self,
        *,
        agent_id: str | None = None,
        user_id: str | None = None,
        thread_id: str | None = None,
    ) -> Any | None:
        """Create a Redis context provider when configuration and dependency are available."""

        if not (importlib.util.find_spec("agent_framework_redis") and self.redis_url):
            return None

        from agent_framework_redis import RedisProvider

        config_source = self.workflow_config.get("redis", {}).get("provider", {})
        allowed_keys = {
            "index_name",
            "prefix",
            "redis_vectorizer",
            "vector_field_name",
            "vector_algorithm",
            "vector_distance_metric",
            "application_id",
            "agent_id",
            "user_id",
            "thread_id",
            "scope_to_per_operation_thread_id",
            "context_prompt",
            "redis_index",
            "overwrite_index",
        }
        provider_kwargs: dict[str, Any] = {
            key: config_source[key] for key in allowed_keys if key in config_source
        }

        if agent_id is not None:
            provider_kwargs["agent_id"] = agent_id
        if user_id is not None:
            provider_kwargs["user_id"] = user_id
        if thread_id is not None:
            provider_kwargs["thread_id"] = thread_id

        return RedisProvider(redis_url=self.redis_url, **provider_kwargs)

    def create_context_providers(
        self,
        *,
        agent_id: str | None = None,
        user_id: str | None = None,
        thread_id: str | None = None,
    ) -> list[Any]:
        """Return all configured context providers for the current environment."""

        providers: list[Any] = []

        redis_provider = self.create_redis_provider(
            agent_id=agent_id,
            user_id=user_id,
            thread_id=thread_id,
        )
        if redis_provider is not None:
            providers.append(redis_provider)

        return providers

    @property
    def openai_api_key(self) -> str | None:
        """Return the configured OpenAI API key if present (may be None)."""

        return self._openai_api_key

    def require_openai_api_key(self) -> str:
        """
        Return the OpenAI API key or raise if missing.

        Raises:
            AgentConfigurationError: If the OPENAI_API_KEY env var is not configured.
        """
        if not self._openai_api_key:
            raise AgentConfigurationError("OPENAI_API_KEY environment variable is required")
        return self._openai_api_key

    def _rewrite_runtime_path(
        self,
        raw_value: str,
        *,
        env_var_name: str | None,
        old_prefix: str,
        new_prefix: str,
    ) -> str:
        """Remap legacy runtime paths (e.g., logs/, checkpoints/) into var/."""

        if env_var_name:
            override_value = os.getenv(env_var_name)
            if override_value:
                override_path = Path(override_value)
                if override_path.is_absolute():
                    return override_value
                override_parts = override_path.parts
                if not override_parts:
                    return override_value
                has_legacy_prefix = override_parts[0] == old_prefix or (
                    len(override_parts) > 1
                    and override_parts[0] == "."
                    and override_parts[1] == old_prefix
                )
                if not has_legacy_prefix:
                    return override_value
                raw_value = override_value

        if not raw_value:
            return raw_value

        path_obj = Path(raw_value)
        new_prefix_parts = Path(new_prefix).parts

        if not path_obj.parts:
            return raw_value

        parts = path_obj.parts

        if parts[0] == old_prefix:
            rewritten = Path(*new_prefix_parts, *parts[1:])
            return str(rewritten)

        if len(parts) > 1 and parts[0] == "." and parts[1] == old_prefix:
            rewritten = Path(".", *new_prefix_parts, *parts[2:])
            return str(rewritten)

        return raw_value


# Global settings instance
settings = Settings()
