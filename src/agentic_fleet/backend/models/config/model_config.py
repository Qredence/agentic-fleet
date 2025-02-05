"""Model configuration manager.

This module provides functionality to load and manage model configurations from
the model pool YAML file. It supports environment variable interpolation and
provides easy access to model capabilities and configurations.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from jinja2 import Template

class ModelConfigError(Exception):
    """Base exception for model configuration errors."""
    pass

class ModelPoolConfig:
    """Manager for model pool configurations."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize model pool configuration.
        
        Args:
            config_path: Path to model pool YAML file. If not provided,
                        uses default path in config directory.
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                "model_pool.yaml"
            )
        
        self.config_path = config_path
        self.config = self._load_config()
    
    def _interpolate_env_vars(self, content: str) -> str:
        """Interpolate environment variables in configuration content.
        
        Args:
            content: Raw configuration content
            
        Returns:
            Configuration content with environment variables interpolated
        """
        template = Template(content)
        return template.render(**os.environ)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load and parse the model pool configuration.
        
        Returns:
            Parsed configuration dictionary
            
        Raises:
            ModelConfigError: If configuration file cannot be loaded or parsed
        """
        try:
            with open(self.config_path, 'r') as f:
                content = f.read()
            
            # Interpolate environment variables
            content = self._interpolate_env_vars(content)
            
            # Parse YAML
            return yaml.safe_load(content)
        except Exception as e:
            raise ModelConfigError(f"Failed to load model configuration: {e}")
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific provider.
        
        Args:
            provider: Provider name (e.g., 'azure_openai', 'deepseek', 'gemini')
            
        Returns:
            Provider configuration dictionary
            
        Raises:
            ModelConfigError: If provider is not found
        """
        if provider not in self.config:
            raise ModelConfigError(f"Provider not found: {provider}")
        return self.config[provider]
    
    def get_model_config(self, provider: str, model_key: str) -> Dict[str, Any]:
        """Get configuration for a specific model.
        
        Args:
            provider: Provider name
            model_key: Model key within provider (e.g., 'gpt4o', 'chat')
            
        Returns:
            Model configuration dictionary
            
        Raises:
            ModelConfigError: If model is not found
        """
        provider_config = self.get_provider_config(provider)
        if 'models' not in provider_config or model_key not in provider_config['models']:
            raise ModelConfigError(f"Model not found: {provider}/{model_key}")
        return provider_config['models'][model_key]
    
    def get_model_by_use_case(self, use_case: str) -> List[Dict[str, Any]]:
        """Find models suitable for a specific use case.
        
        Args:
            use_case: Desired use case (e.g., 'planning', 'analysis')
            
        Returns:
            List of matching model configurations
        """
        matching_models = []
        
        for provider, provider_config in self.config.items():
            for model_key, model_config in provider_config.get('models', {}).items():
                if use_case in model_config.get('use_cases', []):
                    matching_models.append({
                        'provider': provider,
                        'model_key': model_key,
                        **model_config
                    })
        
        return matching_models
    
    def get_models_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Find models with a specific capability.
        
        Args:
            capability: Required capability (e.g., 'vision', 'function_calling')
            
        Returns:
            List of matching model configurations
        """
        matching_models = []
        
        for provider, provider_config in self.config.items():
            for model_key, model_config in provider_config.get('models', {}).items():
                if model_config.get('capabilities', {}).get(capability, False):
                    matching_models.append({
                        'provider': provider,
                        'model_key': model_key,
                        **model_config
                    })
        
        return matching_models

# Create a default instance
default_config = ModelPoolConfig()
