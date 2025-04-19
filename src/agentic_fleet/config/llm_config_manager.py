"""LLM Configuration Manager.

This module provides utilities for loading and managing LLM configurations from YAML files.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class LLMConfigManager:
    """Manager for LLM configurations."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the LLM config manager.

        Args:
            config_path: Path to the LLM configuration YAML file.
                If None, will use the default path.
        """
        self.config_path = config_path or os.path.join(
            Path(__file__).parent.parent.parent.parent, "config", "llm_config.yaml"
        )
        self.config = {}
        self.load_config()

    def load_config(self) -> None:
        """Load the LLM configuration from the YAML file."""
        try:
            with open(self.config_path, "r") as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded LLM configuration from {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading LLM configuration: {e}")
            # Initialize with empty config
            self.config = {"models": {}, "profiles": {}}

    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get the configuration for a specific model.

        Args:
            model_name: The name of the model to get the configuration for.

        Returns:
            The model configuration dictionary.

        Raises:
            ValueError: If the model is not found in the configuration.
        """
        models = self.config.get("models", {})
        if model_name not in models:
            raise ValueError(f"Model {model_name} not found in configuration")
        return models[model_name]

    def get_profile_config(self, profile_name: str) -> Dict[str, Any]:
        """Get the configuration for a specific profile.

        Args:
            profile_name: The name of the profile to get the configuration for.

        Returns:
            The profile configuration dictionary.

        Raises:
            ValueError: If the profile is not found in the configuration.
        """
        profiles = self.config.get("profiles", {})
        if profile_name not in profiles:
            # If profile not found, return the default profile
            if "default" in profiles:
                logger.warning(f"Profile {profile_name} not found, using default")
                return profiles["default"]
            raise ValueError(f"Profile {profile_name} not found in configuration")
        return profiles[profile_name]

    def get_model_for_profile(self, profile_name: str) -> Dict[str, Any]:
        """Get the model configuration for a specific profile.

        Args:
            profile_name: The name of the profile to get the model for.

        Returns:
            The model configuration dictionary for the profile.

        Raises:
            ValueError: If the profile or model is not found in the configuration.
        """
        profile = self.get_profile_config(profile_name)
        model_name = profile.get("model")
        if not model_name:
            raise ValueError(f"No model specified for profile {profile_name}")
        return self.get_model_config(model_name)

    def get_all_models(self) -> Dict[str, Dict[str, Any]]:
        """Get all available models.

        Returns:
            Dictionary of all model configurations.
        """
        return self.config.get("models", {})

    def get_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get all available profiles.

        Returns:
            Dictionary of all profile configurations.
        """
        return self.config.get("profiles", {})


# Create a singleton instance
llm_config_manager = LLMConfigManager()
