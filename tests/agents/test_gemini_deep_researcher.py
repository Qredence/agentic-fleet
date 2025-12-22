"""Tests for Gemini Deep Researcher agent configuration and initialization."""

from __future__ import annotations

import pytest
import yaml
from pathlib import Path

from agentic_fleet.agents.coordinator import AgentFactory
from agentic_fleet.agents.prompts import get_gemini_deep_researcher_instructions


def test_gemini_deep_researcher_prompt_exists():
    """Test that Gemini Deep Researcher prompt function exists and returns valid content."""
    instructions = get_gemini_deep_researcher_instructions()
    
    assert instructions is not None
    assert isinstance(instructions, str)
    assert len(instructions) > 0
    assert "Gemini Deep Researcher" in instructions
    assert "research" in instructions.lower()
    assert "Multi-layered Search" in instructions or "Deep Analysis" in instructions


def test_gemini_deep_researcher_in_workflow_config():
    """Test that Gemini Deep Researcher is configured in workflow_config.yaml."""
    # Find the workflow config file
    config_path = Path(__file__).parent.parent.parent / "src" / "agentic_fleet" / "config" / "workflow_config.yaml"
    
    assert config_path.exists(), f"Config file not found at {config_path}"
    
    with config_path.open("r") as f:
        config = yaml.safe_load(f)
    
    # Check that the agent is configured
    assert "agents" in config
    assert "gemini_deep_researcher" in config["agents"]
    
    agent_config = config["agents"]["gemini_deep_researcher"]
    
    # Validate required fields
    assert "model" in agent_config
    assert "tools" in agent_config
    assert "temperature" in agent_config
    assert "instructions" in agent_config
    assert agent_config["instructions"] == "prompts.gemini_deep_researcher"
    
    # Validate recommended fields
    assert "enable_dspy" in agent_config
    assert agent_config["enable_dspy"] is True
    assert "cache_ttl" in agent_config
    assert "timeout" in agent_config
    
    # Validate tools are configured
    assert isinstance(agent_config["tools"], list)
    assert len(agent_config["tools"]) > 0


def test_gemini_deep_researcher_in_api_config():
    """Test that Gemini Deep Researcher is included in API chat configuration."""
    config_path = Path(__file__).parent.parent.parent / "src" / "agentic_fleet" / "config" / "workflow_config.yaml"
    
    with config_path.open("r") as f:
        config = yaml.safe_load(f)
    
    # Check API configuration
    assert "api" in config
    assert "chat" in config["api"]
    assert "included_agent_ids" in config["api"]["chat"]
    
    included_agents = config["api"]["chat"]["included_agent_ids"]
    assert "gemini_deep_researcher" in included_agents


def test_gemini_deep_researcher_agent_creation(monkeypatch):
    """Test that Gemini Deep Researcher agent can be created via AgentFactory."""
    # Set required environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")
    
    # Mock configuration for the agent (without tools to avoid TAVILY_API_KEY requirement)
    agent_config = {
        "model": "gpt-4.1-mini",
        "tools": [],
        "temperature": 0.6,
        "instructions": "prompts.gemini_deep_researcher",
        "enable_dspy": True,
        "cache_ttl": 600,
        "timeout": 180,
    }
    
    factory = AgentFactory()
    
    # This should not raise an exception
    agent = factory.create_agent("gemini_deep_researcher", agent_config)
    
    # Validate agent properties
    assert agent is not None
    assert agent.name == "Gemini_deep_researcherAgent"
    
    # Check that instructions were resolved
    chat_options = getattr(agent, "chat_options", None)
    if chat_options:
        instructions = getattr(chat_options, "instructions", None)
        if instructions:
            assert "Gemini Deep Researcher" in instructions


def test_gemini_deep_researcher_prompt_structure():
    """Test that Gemini Deep Researcher prompt has expected structure."""
    instructions = get_gemini_deep_researcher_instructions()
    
    # Check for key sections
    key_phrases = [
        "research methodology",
        "Multi-layered Search",
        "Deep Analysis",
        "Comprehensive Synthesis",
        "Source Citation",
    ]
    
    for phrase in key_phrases:
        assert phrase in instructions, f"Missing key phrase: {phrase}"
    
    # Check for guidance on tool usage
    assert "tools" in instructions.lower() or "search" in instructions.lower()
