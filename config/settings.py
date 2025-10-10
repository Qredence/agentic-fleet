import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings with environment variable support."""

    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5")

        # Load workflow configuration (centralized workflow settings)
        self.workflow_config = self._load_yaml("config/workflow_config.yaml")

    def _load_yaml(self, file_path: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        try:
            with open(file_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {}

    def load_agent_config(self, agent_path: str) -> Dict[str, Any]:
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
