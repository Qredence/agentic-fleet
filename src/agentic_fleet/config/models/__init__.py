"""Configuration models and loaders for AgenticFleet."""

import os
from pathlib import Path
from typing import Dict, Optional

import yaml

# Configuration file paths
CONFIG_DIR = Path(__file__).parent
LLM_CONFIG_PATH = CONFIG_DIR / "llm_config.yaml"
AGENT_POOL_CONFIG_PATH = CONFIG_DIR / "agent_pool.yaml"
FLEET_CONFIG_PATH = CONFIG_DIR / "fleet_config.yaml"

def load_yaml_config(path: Path) -> Dict:
    """Load YAML configuration file.

    Args:
        path: Path to YAML configuration file

    Returns:
        Dict containing configuration data

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        yaml.YAMLError: If configuration file is invalid
    """
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing configuration file {path}: {e}")

def load_llm_config() -> Dict:
    """Load LLM configuration."""
    return load_yaml_config(LLM_CONFIG_PATH)

def load_agent_pool_config() -> Dict:
    """Load agent pool configuration."""
    return load_yaml_config(AGENT_POOL_CONFIG_PATH)

def load_fleet_config() -> Dict:
    """Load fleet configuration."""
    return load_yaml_config(FLEET_CONFIG_PATH)

def load_all_configs() -> Dict:
    """Load all configurations.
    
    Returns:
        Dict containing all configuration data
    """
    return {
        "llm": load_llm_config(),
        "agent_pool": load_agent_pool_config(),
        "fleet": load_fleet_config()
    }

def get_model_config(provider: str, model_name: Optional[str] = None) -> Dict:
    """Get configuration for specific model.
    
    Args:
        provider: Model provider name (e.g., 'azure', 'openai')
        model_name: Optional specific model name
        
    Returns:
        Dict containing model configuration
    """
    config = load_llm_config()
    provider_config = config["providers"].get(provider, {})
    
    if not model_name:
        return provider_config
        
    if provider == "azure":
        return provider_config.get("models", {}).get(model_name, {})
    
    return provider_config

def get_agent_config(agent_name: str) -> Dict:
    """Get configuration for specific agent.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Dict containing agent configuration
    """
    config = load_agent_pool_config()
    return config["agents"].get(agent_name, {})

def get_team_config(team_name: str) -> Dict:
    """Get configuration for specific team.
    
    Args:
        team_name: Name of the team
        
    Returns:
        Dict containing team configuration
    """
    config = load_agent_pool_config()
    return config["teams"].get(team_name, {})

# Export configuration paths
__all__ = [
    "LLM_CONFIG_PATH",
    "AGENT_POOL_CONFIG_PATH", 
    "FLEET_CONFIG_PATH",
    "load_yaml_config",
    "load_llm_config",
    "load_agent_pool_config",
    "load_fleet_config",
    "load_all_configs",
    "get_model_config",
    "get_agent_config",
    "get_team_config"
]
