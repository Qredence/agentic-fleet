"""Tests for environment variable validation."""

from __future__ import annotations

import pytest

from agentic_fleet.utils.env import (
    get_env_var,
    validate_agentic_fleet_env,
    validate_required_env_vars,
)
from agentic_fleet.workflows.exceptions import ConfigurationError


def test_validate_required_env_vars_success(monkeypatch):
    """Test successful validation of required environment variables."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")

    # Should not raise
    validate_required_env_vars(["OPENAI_API_KEY"], ["TAVILY_API_KEY"])


def test_validate_required_env_vars_missing(monkeypatch):
    """Test that missing required env vars raise ConfigurationError."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ConfigurationError) as exc_info:
        validate_required_env_vars(["OPENAI_API_KEY"])
    assert "Missing required environment variables" in str(exc_info.value)


def test_validate_required_env_vars_empty(monkeypatch):
    """Test that empty env vars are treated as missing."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    with pytest.raises(ConfigurationError) as exc_info:
        validate_required_env_vars(["OPENAI_API_KEY"])
    assert "Missing required environment variables" in str(exc_info.value)


def test_validate_agentic_fleet_env_success(monkeypatch):
    """Test successful validation of AgenticFleet environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    # Should not raise
    validate_agentic_fleet_env()


def test_validate_agentic_fleet_env_missing(monkeypatch):
    """Test that missing OPENAI_API_KEY raises ConfigurationError."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ConfigurationError) as exc_info:
        validate_agentic_fleet_env()
    assert "OPENAI_API_KEY" in str(exc_info.value)


def test_validate_agentic_fleet_env_cosmos_success_with_key(monkeypatch):
    """Cosmos DB validation passes when enabled and required vars are set with key."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setenv("AGENTICFLEET_USE_COSMOS", "true")
    monkeypatch.setenv("AZURE_COSMOS_ENDPOINT", "https://example.documents.azure.com:443/")
    monkeypatch.setenv("AZURE_COSMOS_DATABASE", "agentic-fleet")
    monkeypatch.setenv("AZURE_COSMOS_KEY", "fake-key")

    # Should not raise
    validate_agentic_fleet_env()


def test_validate_agentic_fleet_env_cosmos_missing_endpoint(monkeypatch):
    """Cosmos DB validation fails when enabled but endpoint is missing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setenv("AGENTICFLEET_USE_COSMOS", "true")
    monkeypatch.delenv("AZURE_COSMOS_ENDPOINT", raising=False)
    monkeypatch.setenv("AZURE_COSMOS_DATABASE", "agentic-fleet")
    monkeypatch.setenv("AZURE_COSMOS_KEY", "fake-key")

    with pytest.raises(ConfigurationError) as exc_info:
        validate_agentic_fleet_env()
    assert "AZURE_COSMOS_ENDPOINT" in str(exc_info.value)


def test_validate_agentic_fleet_env_cosmos_managed_identity(monkeypatch):
    """Cosmos validation allows missing key when managed identity is enabled."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setenv("AGENTICFLEET_USE_COSMOS", "true")
    monkeypatch.setenv("AZURE_COSMOS_ENDPOINT", "https://example.documents.azure.com:443/")
    monkeypatch.setenv("AZURE_COSMOS_DATABASE", "agentic-fleet")
    monkeypatch.setenv("AZURE_COSMOS_USE_MANAGED_IDENTITY", "true")
    monkeypatch.delenv("AZURE_COSMOS_KEY", raising=False)

    # Should not raise even without key
    validate_agentic_fleet_env()


def test_get_env_var_required(monkeypatch):
    """Test getting required environment variable."""
    monkeypatch.setenv("TEST_VAR", "test-value")

    value = get_env_var("TEST_VAR", required=True)
    assert value == "test-value"


def test_get_env_var_required_missing(monkeypatch):
    """Test that missing required env var raises ConfigurationError."""
    monkeypatch.delenv("TEST_VAR", raising=False)

    with pytest.raises(ConfigurationError) as exc_info:
        get_env_var("TEST_VAR", required=True)
    assert "TEST_VAR" in str(exc_info.value)


def test_get_env_var_with_default(monkeypatch):
    """Test getting env var with default value."""
    monkeypatch.delenv("TEST_VAR", raising=False)

    value = get_env_var("TEST_VAR", default="default-value")
    assert value == "default-value"


def test_get_env_var_optional(monkeypatch):
    """Test getting optional environment variable."""
    monkeypatch.delenv("TEST_VAR", raising=False)

    value = get_env_var("TEST_VAR", required=False)
    assert value == ""
