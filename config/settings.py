import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings with environment variable support."""

    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        self.azure_ai_project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        if not self.azure_ai_project_endpoint:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT environment variable is required")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.azure_ai_search_endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
        self.azure_openai_chat_completion_deployed_model_name = os.getenv(
            "AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME"
        )
        self.azure_openai_embedding_deployed_model_name = os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME"
        )

        # Set log file path
        self.log_file = os.getenv("LOG_FILE", "logs/agenticfleet.log")

        self._setup_logging()

        # Load workflow configuration (centralized workflow settings)
        self.workflow_config = self._load_yaml("config/workflow_config.yaml")

    def _setup_logging(self):
        """Configure application-wide logging."""
        logging.basicConfig(
            level=self.log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.log_file),
            ],
        )

    def _load_yaml(self, file_path: str) -> dict[str, Any]:
        """Load YAML configuration file."""
        try:
            with open(file_path) as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logging.warning(f"Configuration file not found: {file_path}")
            return {}

    def load_agent_config(self, agent_path: str) -> dict[str, Any]:
        """
        Load agent-specific configuration from its directory.

        Args:
            agent_path: Path to the agent directory (e.g., 'agents/orchestrator_agent')

        Returns:
            Dict containing agent configuration
        """
        config_path = Path(agent_path) / "agent_config.yaml"
        return self._load_yaml(str(config_path))


settings = Settings()
