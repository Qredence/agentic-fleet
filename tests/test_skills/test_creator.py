"""Tests for skill creator DSPy signatures."""

import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from agentic_fleet.skills.creator import (
    create_hierarchical_context,
    parse_skill_taxonomy,
)


class TestParseSkillTaxonomy:
    """Tests for taxonomy parsing."""

    def test_parse_full_taxonomy(self):
        """Test parsing complete taxonomy path."""
        result = parse_skill_taxonomy("operational/data_processing/extraction")

        assert result["type"] == "operational"
        assert result["category"] == "data_processing"
        assert result["specialization"] == "extraction"

    def test_parse_partial_taxonomy(self):
        """Test parsing partial taxonomy path."""
        result = parse_skill_taxonomy("cognitive/planning")

        assert result["type"] == "cognitive"
        assert result["category"] == "planning"
        assert result["specialization"] == "planning"

    def test_parse_single_element(self):
        """Test parsing single element taxonomy."""
        result = parse_skill_taxonomy("communication")

        assert result["type"] == "communication"
        assert result["category"] == "general"
        assert result["specialization"] == "communication"


class TestCreateHierarchicalContext:
    """Tests for hierarchical context creation."""

    def test_create_full_context(self):
        """Test creating complete hierarchical context."""
        ctx = create_hierarchical_context(
            skill_id="web-research",
            taxonomy="operational/research/web-research",
            trigger_patterns=["research", "search"],
            context_requirements=["browser_tool"],
            depends_on=["base-skill"],
            composes_with=["data-extraction"],
            alternatives=["database-query"],
            domain="web",
            subdomains=["search", "browsing"],
        )

        assert ctx.skill_id == "web-research"
        assert ctx.skill_type.value == "operational"
        assert ctx.category == "research"
        assert ctx.specialization == "web-research"
        assert ctx.knowledge.domain == "web"
        assert "search" in ctx.knowledge.subdomains
        assert "base-skill" in ctx.relational.depends_on
        assert "data-extraction" in ctx.relational.composes_with
        assert "browser_tool" in ctx.context_requirements

    def test_create_minimal_context(self):
        """Test creating context with minimal parameters."""
        ctx = create_hierarchical_context(
            skill_id="test-skill",
            taxonomy="operational/general/test",
            trigger_patterns=["test"],
            context_requirements=[],
        )

        assert ctx.skill_id == "test-skill"
        assert ctx.skill_type.value == "operational"
        assert ctx.category == "general"
        assert ctx.knowledge.domain == "general"
        assert ctx.relational.depends_on == []

    def test_context_memory_keys(self):
        """Test that memory keys are set correctly."""
        ctx = create_hierarchical_context(
            skill_id="code-review",
            taxonomy="operational/software_development/code-review",
            trigger_patterns=["review", "audit"],
            context_requirements=[],
        )

        assert "code-review" in ctx.memory_keys
        assert "code-review" in ctx.memory_keys
        assert "review" in ctx.embedding_keywords
