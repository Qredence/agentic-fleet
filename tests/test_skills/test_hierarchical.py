"""Tests for hierarchical context models and taxonomy."""

import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from agentic_fleet.skills.models import (
    SkillType,
    SkillCategory,
    SkillSpecialization,
    SkillKnowledge,
    SkillRelationalContext,
    HierarchicalSkillContext,
    SkillMemoryIndex,
)


class TestSkillType:
    """Tests for SkillType enum."""

    def test_skill_types(self):
        """Test all skill types are defined."""
        assert SkillType.OPERATIONAL.value == "operational"
        assert SkillType.COGNITIVE.value == "cognitive"
        assert SkillType.COMMUNICATION.value == "communication"
        assert SkillType.DOMAIN.value == "domain"

    def test_skill_type_string_conversion(self):
        """Test string to enum conversion."""
        skill_type = SkillType("operational")
        assert skill_type == SkillType.OPERATIONAL


class TestHierarchicalSkillContext:
    """Tests for HierarchicalSkillContext model."""

    def test_create_context(self):
        """Test creating hierarchical skill context."""
        knowledge = SkillKnowledge(
            domain="web",
            subdomains=["search", "browsing"],
            knowledge_graph_relations=[],
        )
        relational = SkillRelationalContext(
            depends_on=[],
            composes_with=["data-extraction"],
        )

        ctx = HierarchicalSkillContext(
            skill_id="web-research",
            skill_type=SkillType.OPERATIONAL,
            category="research",
            specialization="web-research",
            knowledge=knowledge,
            relational=relational,
            memory_keys=["web", "research"],
            embedding_keywords=["search", "browse"],
            trigger_patterns=["research", "look up"],
            context_requirements=["browser_tool", "search_tool"],
        )

        assert ctx.skill_id == "web-research"
        assert ctx.skill_type == SkillType.OPERATIONAL
        assert ctx.category == "research"
        assert ctx.knowledge.domain == "web"
        assert len(ctx.trigger_patterns) == 2

    def test_context_serialization(self):
        """Test context can be serialized and deserialized."""
        knowledge = SkillKnowledge(domain="software", subdomains=[], knowledge_graph_relations=[])
        relational = SkillRelationalContext(
            depends_on=["test-skill"],
            alternatives=["other-skill"],
        )

        ctx = HierarchicalSkillContext(
            skill_id="code-review",
            skill_type=SkillType.OPERATIONAL,
            category="software_development",
            specialization="code-review",
            knowledge=knowledge,
            relational=relational,
            memory_keys=[],
            embedding_keywords=[],
            trigger_patterns=[],
            context_requirements=[],
        )

        data = ctx.model_dump()
        assert data["skill_id"] == "code-review"
        assert data["skill_type"] == "operational"
        assert data["relational"]["depends_on"] == ["test-skill"]


class TestSkillMemoryIndex:
    """Tests for SkillMemoryIndex model."""

    def test_create_index(self):
        """Test creating skill memory index."""
        index = SkillMemoryIndex(
            skill_id="web-research",
            hierarchical_path="operational/research/web-research",
            keywords=["web", "research", "search"],
            capability_tags=["search", "extraction"],
            domain_tags=["web"],
        )

        assert index.skill_id == "web-research"
        assert "research" in index.keywords
        assert index.usage_count == 0
        assert index.success_rate == 0.0

    def test_index_with_embedding(self):
        """Test index with embedding vector."""
        embedding = [0.1, 0.2, 0.3, 0.4]
        index = SkillMemoryIndex(
            skill_id="test-skill",
            hierarchical_path="operational/general/test",
            embedding_vector=embedding,
            keywords=[],
            capability_tags=[],
            domain_tags=[],
        )

        assert index.embedding_vector == embedding
        assert len(index.embedding_vector) == 4


class TestSkillKnowledge:
    """Tests for SkillKnowledge model."""

    def test_create_knowledge(self):
        """Test creating skill knowledge."""
        knowledge = SkillKnowledge(
            domain="software",
            subdomains=["testing", "quality"],
            knowledge_graph_relations=[
                {"relation": "part_of", "target": "software-development"}
            ],
        )

        assert knowledge.domain == "software"
        assert "testing" in knowledge.subdomains
        assert len(knowledge.knowledge_graph_relations) == 1


class TestSkillRelationalContext:
    """Tests for SkillRelationalContext model."""

    def test_create_relational_context(self):
        """Test creating relational context."""
        relational = SkillRelationalContext(
            depends_on=["base-skill"],
            composes_with=["other-skill"],
            alternatives=["legacy-skill"],
            supersedes=["old-skill"],
            related_skills=["related-1", "related-2"],
        )

        assert "base-skill" in relational.depends_on
        assert "other-skill" in relational.composes_with
        assert "legacy-skill" in relational.alternatives
        assert "old-skill" in relational.supersedes
        assert len(relational.related_skills) == 2

    def test_default_values(self):
        """Test default values for relational context."""
        relational = SkillRelationalContext()

        assert relational.depends_on == []
        assert relational.composes_with == []
        assert relational.alternatives == []
        assert relational.supersedes == []
        assert relational.related_skills == []
