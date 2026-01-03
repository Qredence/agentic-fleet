"""Unit tests for RouterAgent."""

import pytest
import sys
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

import dspy

from agentic_fleet.agents.router import RouterAgent


class TestRouterAgent:
    """Tests for RouterAgent."""

    def test_router_agent_creation(self, reset_team_registry):
        """Test RouterAgent can be instantiated."""
        agent = RouterAgent()
        assert agent.name == "Router"
        assert agent.role == "dispatcher"  # RouterAgent uses "dispatcher" role

    @pytest.mark.asyncio
    async def test_router_extracts_complex_pattern(self, reset_team_registry, routing_lm):
        """Test RouterAgent extracts complex pattern from response."""
        with dspy.context(lm=routing_lm(pattern="complex")):
            agent = RouterAgent()
            response = await agent.run("Research AI trends")

            assert response.additional_properties is not None
            assert response.additional_properties.get("route_pattern") == "complex"

    @pytest.mark.asyncio
    async def test_router_extracts_simple_pattern(self, reset_team_registry, routing_lm):
        """Test RouterAgent extracts simple pattern from response."""
        with dspy.context(lm=routing_lm(pattern="simple")):
            agent = RouterAgent()
            response = await agent.run("What is the weather?")

            assert response.additional_properties is not None
            assert response.additional_properties.get("route_pattern") == "simple"

    @pytest.mark.asyncio
    async def test_router_extracts_direct_pattern(self, reset_team_registry, routing_lm):
        """Test RouterAgent extracts direct pattern from response."""
        with dspy.context(lm=routing_lm(pattern="direct")):
            agent = RouterAgent()
            response = await agent.run("Hello")

            assert response.additional_properties is not None
            assert response.additional_properties.get("route_pattern") == "direct"

    @pytest.mark.asyncio
    async def test_router_sets_target_team(self, reset_team_registry, routing_lm):
        """Test RouterAgent sets target_team in metadata."""
        with dspy.context(lm=routing_lm(pattern="complex", target_team="research")):
            agent = RouterAgent()
            response = await agent.run("Research something")

            assert response.additional_properties is not None
            assert response.additional_properties.get("target_team") == "research"

    @pytest.mark.asyncio
    async def test_router_adds_original_task(self, reset_team_registry, routing_lm):
        """Test RouterAgent includes original task in metadata."""
        with dspy.context(lm=routing_lm(pattern="simple")):
            agent = RouterAgent()
            test_task = "Test task for routing"
            response = await agent.run(test_task)

            assert response.additional_properties is not None
            assert "Test task" in response.additional_properties.get("original_task", "")


class TestRouterAgentRoutingPatterns:
    """Tests for different routing patterns."""

    @pytest.mark.asyncio
    async def test_complex_pattern_uses_research_team(self, reset_team_registry, routing_lm):
        """Test complex pattern typically routes to research team."""
        with dspy.context(lm=routing_lm(pattern="complex", target_team="research")):
            agent = RouterAgent()
            response = await agent.run("Research the latest developments in AI")

            assert response.additional_properties.get("route_pattern") == "complex"
            assert response.additional_properties.get("target_team") == "research"

    @pytest.mark.asyncio
    async def test_simple_pattern_uses_default_team(self, reset_team_registry, routing_lm):
        """Test simple pattern typically routes to default team."""
        with dspy.context(lm=routing_lm(pattern="simple", target_team="default")):
            agent = RouterAgent()
            response = await agent.run("What is 2+2?")

            assert response.additional_properties.get("route_pattern") == "simple"
            assert response.additional_properties.get("target_team") == "default"

    @pytest.mark.asyncio
    async def test_direct_pattern_uses_default_team(self, reset_team_registry, routing_lm):
        """Test direct pattern routes to default team."""
        with dspy.context(lm=routing_lm(pattern="direct", target_team="default")):
            agent = RouterAgent()
            response = await agent.run("Hi")

            assert response.additional_properties.get("route_pattern") == "direct"
            assert response.additional_properties.get("target_team") == "default"
