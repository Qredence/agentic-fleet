"""Comprehensive tests for utils/config.py."""

import os
from unittest.mock import patch

import pytest

from agentic_fleet.utils.cfg import EnvConfig, load_config, validate_config
from agentic_fleet.workflows.exceptions import ConfigurationError


class TestLoadConfig:
    """Test suite for load_config function."""

    @pytest.fixture
    def sample_config_yaml(self):
        """Provide sample YAML configuration."""
        return """
workflow:
  supervisor:
    max_rounds: 5
agents:
  researcher:
    model: gpt-4.1-mini
    temperature: 0.7
"""

    def test_load_config_success(self, tmp_path):
        """Test successful config loading from an actual file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
workflow:
  supervisor:
    max_rounds: 5
    max_router_retries: 2
"""
        )

        config = load_config(str(config_file))

        assert config is not None
        assert "workflow" in config

    def test_load_config_file_not_found(self):
        """Test loading non-existent config file returns defaults."""
        # Should return default config if file not found
        config = load_config("nonexistent_path_12345.yaml")
        assert config is not None
        assert "workflow" in config

    def test_load_config_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises ConfigurationError."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ConfigurationError):
            load_config(str(config_file))

    def test_load_config_empty(self, tmp_path):
        """Test loading empty config returns defaults."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        # Should return default config if file is empty
        config = load_config(str(config_file))
        assert config is not None
        assert "workflow" in config

    def test_load_config_with_default_path(self):
        """Test loading config with default path."""
        # When no path given, uses built-in defaults or finds package config
        config = load_config()
        assert isinstance(config, dict)
        assert "workflow" in config


class TestValidateConfig:
    """Test suite for validate_config function."""

    @pytest.fixture
    def valid_config(self):
        """Provide valid configuration."""
        return {
            "workflow": {"supervisor": {"max_rounds": 5}},
            "agents": {"researcher": {"model": "gpt-4.1-mini"}},
        }

    def test_validate_config_valid(self, valid_config):
        """Test validation of valid configuration."""
        schema = validate_config(valid_config)
        assert schema is not None
        assert schema.workflow.supervisor.max_rounds == 5

    def test_validate_config_invalid(self):
        """Test validation with invalid config."""
        invalid_config = {"workflow": {"supervisor": {"max_rounds": "not_an_int"}}}

        with pytest.raises(ConfigurationError):
            validate_config(invalid_config)


class TestEnvConfig:
    """Test suite for EnvConfig class."""

    def test_env_config_defaults(self):
        """Test default values."""
        env = EnvConfig()
        env.clear_cache()
        assert env.host == "0.0.0.0"
        assert env.port == 8000

    @patch.dict(os.environ, {"HOST": "127.0.0.1", "PORT": "9000"})
    def test_env_config_overrides(self):
        """Test environment variable overrides."""
        env = EnvConfig()
        env.clear_cache()
        assert env.host == "127.0.0.1"
        assert env.port == 9000
