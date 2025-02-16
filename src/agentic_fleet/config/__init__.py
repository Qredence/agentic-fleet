"""Configuration management for AgenticFleet."""

from pathlib import Path
from typing import Any, Dict, Optional

from agentic_fleet.config.models import (
    load_all_configs,
    get_model_config,
    get_agent_config,
    get_team_config
)
from agentic_fleet.config.settings import (
    load_app_settings,
    validate_env_vars,
    get_app_defaults,
    get_logging_config,
    get_security_config,
    get_environment_config,
    get_performance_config,
    get_api_config,
    get_app_info
)

# Configuration root directory
CONFIG_ROOT = Path(__file__).parent

class ConfigurationManager:
    """Unified configuration management for AgenticFleet."""

    def __init__(self):
        """Initialize configuration manager."""
        self._app_settings = None
        self._model_configs = None
        self._agent_configs = None
        self._fleet_configs = None

    def load_all(self) -> None:
        """Load all configuration files."""
        # Load application settings
        self._app_settings = load_app_settings()

        # Load model, agent, and fleet configurations
        configs = load_all_configs()
        self._model_configs = configs["llm"]
        self._agent_configs = configs["agent_pool"]
        self._fleet_configs = configs["fleet"]

    def validate_environment(self) -> Optional[str]:
        """Validate environment configuration.

        Returns:
            Error message if validation fails, None otherwise
        """
        missing_vars = validate_env_vars()
        if missing_vars:
            return f"Missing required environment variables: {', '.join(missing_vars)}"
        return None

    def get_model_settings(self, provider: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Get model configuration settings.

        Args:
            provider: Model provider name
            model_name: Optional specific model name

        Returns:
            Dict containing model configuration
        """
        if self._model_configs is None:
            self.load_all()
        return get_model_config(provider, model_name)

    def get_agent_settings(self, agent_name: str) -> Dict[str, Any]:
        """Get agent configuration settings.

        Args:
            agent_name: Name of the agent

        Returns:
            Dict containing agent configuration
        """
        if self._agent_configs is None:
            self.load_all()
        return get_agent_config(agent_name)

    def get_team_settings(self, team_name: str) -> Dict[str, Any]:
        """Get team configuration settings.

        Args:
            team_name: Name of the team

        Returns:
            Dict containing team configuration
        """
        if self._agent_configs is None:
            self.load_all()
        return get_team_config(team_name)

    def get_app_settings(self) -> Dict[str, Any]:
        """Get application settings.

        Returns:
            Dict containing application settings
        """
        if self._app_settings is None:
            self._app_settings = load_app_settings()
        return self._app_settings

    def get_defaults(self) -> Dict[str, Any]:
        """Get default settings.

        Returns:
            Dict containing default settings
        """
        return get_app_defaults()

    def get_logging_settings(self) -> Dict[str, Any]:
        """Get logging settings.

        Returns:
            Dict containing logging settings
        """
        return get_logging_config()

    def get_security_settings(self) -> Dict[str, Any]:
        """Get security settings.

        Returns:
            Dict containing security settings
        """
        return get_security_config()

    def get_environment_settings(self) -> Dict[str, Any]:
        """Get environment settings.

        Returns:
            Dict containing environment settings
        """
        return get_environment_config()

    def get_performance_settings(self) -> Dict[str, Any]:
        """Get performance settings.

        Returns:
            Dict containing performance settings
        """
        return get_performance_config()

    def get_api_settings(self) -> Dict[str, Any]:
        """Get API settings.

        Returns:
            Dict containing API settings
        """
        return get_api_config()

# Create global configuration manager instance
config_manager = ConfigurationManager()

# Load default values from app_settings.yaml
_app_settings = load_app_settings()
_defaults = _app_settings.get("defaults", {})

# Export default constants
DEFAULT_MAX_ROUNDS = _defaults.get("max_rounds", 10)
DEFAULT_MAX_TIME = _defaults.get("max_time", 300)
DEFAULT_MAX_STALLS = _defaults.get("max_stalls", 3)
DEFAULT_START_PAGE = _defaults.get("start_page", "/welcome")
DEFAULT_TEMPERATURE = _defaults.get("temperature", 0.7)
DEFAULT_SYSTEM_PROMPT = _defaults.get("system_prompt", "You are a helpful AI assistant.")

# Export configuration manager and paths
__all__ = [
    "CONFIG_ROOT",
    "ConfigurationManager",
    "config_manager",
    # Default constants
    "DEFAULT_MAX_ROUNDS",
    "DEFAULT_MAX_TIME",
    "DEFAULT_MAX_STALLS",
    "DEFAULT_START_PAGE",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_SYSTEM_PROMPT",
    # Re-export from models
    "get_model_config",
    "get_agent_config",
    "get_team_config",
    # Re-export from settings
    "get_app_defaults",
    "get_logging_config",
    "get_security_config",
    "get_environment_config",
    "get_performance_config",
    "get_api_config",
    "get_app_info"
]
