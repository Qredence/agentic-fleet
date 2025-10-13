"""Config settings management for AgenticFleet."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from agent_framework import CheckpointStorage, FileCheckpointStorage, InMemoryCheckpointStorage
from dotenv import load_dotenv

from agenticfleet.core.exceptions import AgentConfigurationError
from agenticfleet.core.logging import setup_logging

load_dotenv()


class Settings:
    """Application settings with environment variable support."""

    def __init__(self) -> None:
        """Initialize settings from environment variables and config files."""
        # Required environment variables
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise AgentConfigurationError("OPENAI_API_KEY environment variable is required")

        self.azure_ai_project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        if not self.azure_ai_project_endpoint:
            raise AgentConfigurationError(
                "AZURE_AI_PROJECT_ENDPOINT environment variable is required"
            )

        # Optional environment variables with defaults
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "logs/agenticfleet.log")

        # Azure-specific settings
        self.azure_ai_search_endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
        self.azure_ai_search_key = os.getenv("AZURE_AI_SEARCH_KEY")
        self.azure_openai_chat_completion_deployed_model_name = os.getenv(
            "AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME"
        )
        self.azure_openai_embedding_deployed_model_name = os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME"
        )

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
            raise AgentConfigurationError(f"Failed to parse YAML file {file_path}: {e}")

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
            return InMemoryCheckpointStorage()
        elif storage_type == "file":
            storage_path = checkpoint_config.get("storage_path", "./checkpoints")
            # Ensure the checkpoints directory exists
            Path(storage_path).mkdir(parents=True, exist_ok=True)
            return FileCheckpointStorage(storage_path)
        else:
            logging.warning(
                f"Unknown checkpoint storage type: {storage_type}. Checkpointing disabled."
            )
            return None


# Global settings instance
settings = Settings()
