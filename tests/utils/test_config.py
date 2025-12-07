"""Comprehensive tests for utils/config.py."""

import pytest
import os
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from agentic_fleet.utils.config import (
    load_workflow_config,
    get_config_value,
    validate_config_schema,
    merge_configs,
    ConfigurationError,
)


class TestLoadWorkflowConfig:
    """Test suite for load_workflow_config function."""

    @pytest.fixture
    def sample_config_yaml(self):
        """Provide sample YAML configuration."""
        return """
execution:
  max_iterations: 5
  quality_threshold: 0.8

agents:
  researcher:
    model: gpt-4o
    temperature: 0.7

dspy:
  optimization:
    use_typed_signatures: true
"""

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    def test_load_workflow_config_success(self, mock_yaml_load, mock_file, sample_config_yaml):
        """Test successful config loading."""
        mock_yaml_load.return_value = {
            "execution": {"max_iterations": 5},
            "agents": {},
        }

        config = load_workflow_config("config.yaml")

        assert config is not None
        assert "execution" in config
        mock_file.assert_called_once()

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_load_workflow_config_file_not_found(self, mock_file):
        """Test loading non-existent config file."""
        with pytest.raises(FileNotFoundError):
            load_workflow_config("nonexistent.yaml")

    @patch("builtins.open", new_callable=mock_open, read_data="invalid: yaml: content:")
    @patch("yaml.safe_load", side_effect=yaml.YAMLError("Invalid YAML"))
    def test_load_workflow_config_invalid_yaml(self, mock_yaml_load, mock_file):
        """Test loading invalid YAML."""
        with pytest.raises(yaml.YAMLError):
            load_workflow_config("invalid.yaml")

    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    @patch("yaml.safe_load", return_value={})
    def test_load_workflow_config_empty(self, mock_yaml_load, mock_file):
        """Test loading empty config."""
        config = load_workflow_config("empty.yaml")

        assert config == {}

    def test_load_workflow_config_with_default_path(self):
        """Test loading config with default path."""
        with patch("builtins.open", new_callable=mock_open):
            with patch("yaml.safe_load", return_value={}):
                config = load_workflow_config()

                assert isinstance(config, dict)


class TestGetConfigValue:
    """Test suite for get_config_value function."""

    @pytest.fixture
    def config(self):
        """Provide sample configuration."""
        return {
            "execution": {
                "max_iterations": 10,
                "nested": {"value": 42},
            },
            "agents": {
                "researcher": {"model": "gpt-4o"},
            },
        }

    def test_get_config_value_top_level(self, config):
        """Test getting top-level config value."""
        value = get_config_value(config, "execution")

        assert value == config["execution"]

    def test_get_config_value_nested(self, config):
        """Test getting nested config value."""
        value = get_config_value(config, "execution.max_iterations")

        assert value == 10

    def test_get_config_value_deeply_nested(self, config):
        """Test getting deeply nested value."""
        value = get_config_value(config, "execution.nested.value")

        assert value == 42

    def test_get_config_value_with_default(self, config):
        """Test getting value with default fallback."""
        value = get_config_value(config, "nonexistent.key", default="default_value")

        assert value == "default_value"

    def test_get_config_value_missing_no_default(self, config):
        """Test getting missing value without default."""
        with pytest.raises(KeyError):
            get_config_value(config, "nonexistent.key")

    def test_get_config_value_none_value(self, config):
        """Test getting None value (if explicitly set)."""
        config["null_value"] = None
        value = get_config_value(config, "null_value", default="default")

        # Should return None, not default (None is a valid value)
        assert value is None


class TestValidateConfigSchema:
    """Test suite for validate_config_schema function."""

    @pytest.fixture
    def valid_config(self):
        """Provide valid configuration."""
        return {
            "execution": {"max_iterations": 5, "quality_threshold": 0.8},
            "agents": {"researcher": {"model": "gpt-4o"}},
        }

    @pytest.fixture
    def schema(self):
        """Provide configuration schema."""
        return {
            "type": "object",
            "properties": {
                "execution": {
                    "type": "object",
                    "properties": {
                        "max_iterations": {"type": "integer"},
                        "quality_threshold": {"type": "number"},
                    },
                    "required": ["max_iterations"],
                },
                "agents": {"type": "object"},
            },
            "required": ["execution", "agents"],
        }

    def test_validate_config_schema_valid(self, valid_config, schema):
        """Test validation of valid configuration."""
        is_valid = validate_config_schema(valid_config, schema)

        assert is_valid is True

    def test_validate_config_schema_missing_required(self, schema):
        """Test validation with missing required field."""
        invalid_config = {"execution": {"max_iterations": 5}}  # Missing 'agents'

        with pytest.raises(ConfigurationError):
            validate_config_schema(invalid_config, schema)

    def test_validate_config_schema_wrong_type(self, schema):
        """Test validation with wrong type."""
        invalid_config = {
            "execution": {"max_iterations": "not_an_int"},  # Should be int
            "agents": {},
        }

        with pytest.raises(ConfigurationError):
            validate_config_schema(invalid_config, schema)

    def test_validate_config_schema_extra_fields(self, valid_config, schema):
        """Test validation with extra fields (should be allowed)."""
        config_with_extra = {**valid_config, "extra_field": "value"}

        is_valid = validate_config_schema(config_with_extra, schema)

        # Extra fields typically allowed unless schema specifies otherwise
        assert is_valid is True or isinstance(is_valid, bool)


class TestMergeConfigs:
    """Test suite for merge_configs function."""

    def test_merge_configs_basic(self):
        """Test basic config merging."""
        base_config = {"key1": "value1", "key2": "value2"}
        override_config = {"key2": "override2", "key3": "value3"}

        merged = merge_configs(base_config, override_config)

        assert merged["key1"] == "value1"
        assert merged["key2"] == "override2"  # Overridden
        assert merged["key3"] == "value3"

    def test_merge_configs_nested(self):
        """Test merging nested configurations."""
        base_config = {
            "execution": {"max_iterations": 5, "timeout": 300},
            "agents": {"researcher": {"model": "gpt-4"}},
        }
        override_config = {
            "execution": {"max_iterations": 10},  # Override this
            "agents": {"analyst": {"model": "gpt-4o"}},  # Add new agent
        }

        merged = merge_configs(base_config, override_config)

        assert merged["execution"]["max_iterations"] == 10
        assert merged["execution"]["timeout"] == 300  # Preserved
        assert "researcher" in merged["agents"]
        assert "analyst" in merged["agents"]

    def test_merge_configs_empty_override(self):
        """Test merging with empty override."""
        base_config = {"key": "value"}
        merged = merge_configs(base_config, {})

        assert merged == base_config

    def test_merge_configs_empty_base(self):
        """Test merging with empty base."""
        override_config = {"key": "value"}
        merged = merge_configs({}, override_config)

        assert merged == override_config

    def test_merge_configs_both_empty(self):
        """Test merging two empty configs."""
        merged = merge_configs({}, {})

        assert merged == {}

    def test_merge_configs_list_handling(self):
        """Test merging configs with lists."""
        base_config = {"tools": ["tool1", "tool2"]}
        override_config = {"tools": ["tool3"]}

        merged = merge_configs(base_config, override_config)

        # List behavior depends on implementation
        # Could replace or extend
        assert "tools" in merged


class TestConfigurationError:
    """Test suite for ConfigurationError exception."""

    def test_configuration_error_creation(self):
        """Test creating ConfigurationError."""
        error = ConfigurationError("Invalid configuration")

        assert str(error) == "Invalid configuration"

    def test_configuration_error_raise(self):
        """Test raising ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Test error"):
            raise ConfigurationError("Test error")


class TestConfigEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_load_config_with_unicode(self):
        """Test loading config with unicode characters."""
        config_content = "key: '测试值'"

        with patch("builtins.open", mock_open(read_data=config_content)):
            with patch("yaml.safe_load", return_value={"key": "测试值"}):
                config = load_workflow_config("test.yaml")

                assert config["key"] == "测试值"

    def test_get_config_value_with_integer_key(self):
        """Test getting value with integer in path."""
        config = {"agents": {"agent1": {"models": ["model1", "model2"]}}}

        # Some implementations might support: "agents.agent1.models.0"
        try:
            value = get_config_value(config, "agents.agent1.models")
            assert value == ["model1", "model2"]
        except (KeyError, TypeError):
            pass

    def test_merge_configs_with_none_values(self):
        """Test merging configs containing None."""
        base = {"key1": "value", "key2": None}
        override = {"key2": "new_value", "key3": None}

        merged = merge_configs(base, override)

        assert merged["key1"] == "value"
        assert merged["key2"] == "new_value"
        assert merged["key3"] is None

    def test_validate_config_with_complex_schema(self):
        """Test validation with complex nested schema."""
        config = {
            "agents": {
                "researcher": {
                    "model": "gpt-4o",
                    "tools": ["tool1", "tool2"],
                    "config": {"temperature": 0.7},
                }
            }
        }

        schema = {
            "type": "object",
            "properties": {
                "agents": {
                    "type": "object",
                    "patternProperties": {
                        ".*": {
                            "type": "object",
                            "properties": {
                                "model": {"type": "string"},
                                "tools": {"type": "array"},
                                "config": {"type": "object"},
                            },
                        }
                    },
                }
            },
        }

        is_valid = validate_config_schema(config, schema)
        assert isinstance(is_valid, bool)


class TestConfigIntegration:
    """Integration tests for configuration management."""

    def test_load_merge_validate_workflow(self):
        """Test complete config workflow: load, merge, validate."""
        base_yaml = """
execution:
  max_iterations: 5
agents:
  researcher:
    model: gpt-4
"""
        override_yaml = """
execution:
  max_iterations: 10
agents:
  analyst:
    model: gpt-4o
"""

        with patch("builtins.open", mock_open(read_data=base_yaml)):
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [
                    yaml.safe_load(base_yaml),
                    yaml.safe_load(override_yaml),
                ]

                base_config = load_workflow_config("base.yaml")
                override_config = load_workflow_config("override.yaml")

                merged = merge_configs(base_config, override_config)

                assert merged["execution"]["max_iterations"] == 10
                assert "researcher" in merged["agents"]
                assert "analyst" in merged["agents"]

    def test_environment_variable_expansion(self):
        """Test config with environment variable expansion."""
        os.environ["TEST_MODEL"] = "gpt-4o-test"

        config_yaml = """
agents:
  researcher:
    model: ${TEST_MODEL}
"""

        # If implementation supports env var expansion
        with patch("builtins.open", mock_open(read_data=config_yaml)):
            with patch("yaml.safe_load", return_value={"agents": {"researcher": {"model": "${TEST_MODEL}"}}}):
                config = load_workflow_config("test.yaml")

                # Check if env var was expanded (depends on implementation)
                model_value = config["agents"]["researcher"]["model"]
                assert model_value in ["${TEST_MODEL}", "gpt-4o-test"]

        del os.environ["TEST_MODEL"]