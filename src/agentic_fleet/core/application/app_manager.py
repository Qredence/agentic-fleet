"""Application manager for AgenticFleet."""

import logging
import os
from typing import Any, Callable, List, Optional

import yaml
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ModelConfigSettings:
    """Model configuration settings loaded from model_config.yaml."""

    def __init__(self, model_configs: dict):
        # Azure OpenAI settings with proper defaults from model_config.yaml
        # Load Azure OpenAI deployment from model_config.yaml
        default_deployment = model_configs.get("azure", {}).get("config", {}).get("azure_deployment", "o3-mini")
        # Load Azure OpenAI settings from environment variables with defaults from model_config.yaml
        self.AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", default_deployment)
        self.AZURE_OPENAI_MODEL: str = os.getenv("AZURE_OPENAI_MODEL")
        self.AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.AZURE_OPENAI_API_KEY: Optional[str] = os.getenv("AZURE_OPENAI_API_KEY")
        self.AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

        # Validate required settings
        if not self.AZURE_OPENAI_ENDPOINT or not self.AZURE_OPENAI_API_KEY:
            raise ValueError(
                "Missing required Azure OpenAI configuration: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set"
            )


class FleetConfigSettings:
    """Fleet configuration settings loaded from fleet_config.yaml."""

    def __init__(self, fleet_config: dict):
        self.DEFAULT_MAX_ROUNDS: int = fleet_config.get("DEFAULT_MAX_ROUNDS", 50)
        self.DEFAULT_MAX_TIME: int = fleet_config.get("DEFAULT_MAX_TIME", 10)  # minutes
        self.DEFAULT_MAX_STALLS: int = fleet_config.get("DEFAULT_MAX_STALLS", 5)
        self.DEFAULT_START_PAGE: str = fleet_config.get("DEFAULT_START_PAGE", "https://bing.com")


class Settings(ModelConfigSettings, FleetConfigSettings):
    """Application settings loaded from environment variables."""

    def __init__(self, model_configs: dict, fleet_config: dict):
        ModelConfigSettings.__init__(self, model_configs)
        FleetConfigSettings.__init__(self, fleet_config)

        load_dotenv()

        from agentic_fleet.config import (
            config_manager,
            DEFAULT_TEMPERATURE,
            DEFAULT_MAX_ROUNDS,
            DEFAULT_MAX_TIME,
            DEFAULT_SYSTEM_PROMPT,
            # DEFAULT_START_PAGE, # Not used in Settings class currently
            # DEFAULT_MAX_STALLS, # Not used in Settings class currently
        )

        # OAuth settings
        # Default for USE_OAUTH comes from app_settings.yaml via config_manager
        self.USE_OAUTH: bool = os.getenv("USE_OAUTH", str(config_manager.get_security_settings().use_oauth)).lower() == "true"
        self.OAUTH_PROVIDERS: List[str] = os.getenv("OAUTH_PROVIDERS", "" if not config_manager.get_security_settings().oauth_providers else ",".join(provider.name for provider in config_manager.get_security_settings().oauth_providers if provider.name)).split(",")


        # Chat settings - defaults now come from config_manager via imported constants
        # These constants (DEFAULT_TEMPERATURE, etc.) are loaded from app_settings.yaml in config/__init__.py
        self.temperature: float = float(os.getenv("DEFAULT_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
        self.max_rounds: int = int(os.getenv("DEFAULT_MAX_ROUNDS", str(DEFAULT_MAX_ROUNDS)))
        self.max_time: int = int(os.getenv("DEFAULT_MAX_TIME", str(DEFAULT_MAX_TIME)))
        self.system_prompt: str = os.getenv("DEFAULT_SYSTEM_PROMPT", str(DEFAULT_SYSTEM_PROMPT))


class ApplicationManager:
    """Manages application lifecycle and resources."""

    def __init__(self, model_client: AzureOpenAIChatCompletionClient):
        """Initialize application manager.

        Args:
            model_client: Azure OpenAI client for LLM interactions
        """
        config_path = os.path.join(os.path.dirname(__file__), "models", "model_config.yaml")
        try:
            with open(config_path, "r") as f:
                self.model_configs = yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Model configuration file not found: {config_path}")
            self.model_configs = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing model configuration file: {e}")
            self.model_configs = {}

        # Load fleet configuration from YAML file
        fleet_config_path = os.path.join(os.path.dirname(__file__), "models", "fleet_config.yaml")
        try:
            with open(fleet_config_path, "r") as f:
                self.fleet_config = yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Fleet configuration file not found: {fleet_config_path}")
            self.fleet_config = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing fleet configuration file: {e}")
            self.fleet_config = {}

        self.settings = Settings(self.model_configs, self.fleet_config)
        self.model_client = model_client
        self._initialized = False
        self._cleanup_handlers: List[Callable[[], Any]] = []

        # Set default model provider to Azure
        self.default_model_provider = "azure"

    async def start(self) -> None:
        """Start the application and initialize resources."""
        if self._initialized:
            logger.warning("Application already initialized")
            return

        try:
            logger.info("Starting application...")
            # Initialize resources here
            self._initialized = True
            logger.info("Application started successfully")

        except Exception as e:
            logger.error(f"Failed to start application: {str(e)}")
            raise

    async def stop(self) -> None:
        """Stop the application and cleanup resources."""
        if not self._initialized:
            logger.warning("Application not initialized")
            return

        try:
            logger.info("Stopping application...")

            # Run cleanup handlers
            for handler in self._cleanup_handlers:
                try:
                    await handler()
                except Exception as e:
                    logger.error(f"Cleanup handler failed: {str(e)}")

            self._initialized = False
            logger.info("Application stopped successfully")

        except Exception as e:
            logger.error(f"Failed to stop application: {str(e)}")
            raise

    def add_cleanup_handler(self, handler: Callable[[], Any]) -> None:
        """Add a cleanup handler to be called on application stop.

        Args:
            handler: Async function to be called during cleanup
        """
        self._cleanup_handlers.append(handler)

    @property
    def initialized(self) -> bool:
        """Check if application is initialized.

        Returns:
            True if application is initialized, False otherwise
        """
        return self._initialized
