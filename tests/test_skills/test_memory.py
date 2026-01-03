"""Tests for skill memory system integration."""

import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from agentic_fleet.skills.memory import (
    SkillMemoryIndexStore,
    SkillRetrievalService,
)
from agentic_fleet.skills.models import Skill, SkillMetadata, SkillContent


class TestSkillMemoryIndexStore:
    """Tests for SkillMemoryIndexStore."""

    @pytest.fixture
    def sample_skill(self):
        """Create a sample skill for testing."""
        return Skill(
            metadata=SkillMetadata(
                skill_id="web-research",
                name="Web Research",
                version="1.0.0",
                description="Perform web research",
                team_id="research",
                tags=["research", "search"],
            ),
            content=SkillContent(
                purpose="Extract information",
                when_to_use="Need current info",
                how_to_apply="Search and browse",
                example="Research quantum computing",
            ),
        )

    def test_index_skill(self, sample_skill):
        """Test indexing a skill."""
        store = SkillMemoryIndexStore()
        index = store.index_skill(sample_skill)

        assert index.skill_id == "web-research"
        assert index.hierarchical_path == "operational/research/web-research"
        assert "research" in index.keywords

    def test_get_index(self, sample_skill):
        """Test retrieving an index."""
        store = SkillMemoryIndexStore()
        store.index_skill(sample_skill)

        index = store.get_index("web-research")
        assert index is not None
        assert index.skill_id == "web-research"

    def test_get_nonexistent_index(self):
        """Test retrieving nonexistent index returns None."""
        store = SkillMemoryIndexStore()
        index = store.get_index("nonexistent")
        assert index is None

    def test_update_usage(self, sample_skill):
        """Test updating usage statistics."""
        store = SkillMemoryIndexStore()
        store.index_skill(sample_skill)

        store.update_usage("web-research", successful=True, execution_time_ms=100)

        index = store.get_index("web-research")
        assert index.usage_count == 1

    def test_search_by_keyword(self, sample_skill):
        """Test searching by keyword."""
        store = SkillMemoryIndexStore()
        store.index_skill(sample_skill)

        results = store.search_by_keyword(["research"])
        assert len(results) == 1
        assert results[0].skill_id == "web-research"

    def test_search_by_hierarchy(self, sample_skill):
        """Test searching by hierarchy."""
        store = SkillMemoryIndexStore()
        store.index_skill(sample_skill)

        from agentic_fleet.skills.models import SkillType

        results = store.search_by_hierarchy(
            skill_type=SkillType.OPERATIONAL,
            category="research",
        )
        assert len(results) == 1

    def test_search_by_capability(self, sample_skill):
        """Test searching by capability tag."""
        store = SkillMemoryIndexStore()
        store.index_skill(sample_skill)

        results = store.search_by_capability("search")
        assert len(results) == 1

    def test_list_all(self, sample_skill):
        """Test listing all indexes."""
        store = SkillMemoryIndexStore()
        store.index_skill(sample_skill)

        all_indexes = store.list_all()
        assert len(all_indexes) == 1


class TestSkillRetrievalService:
    """Tests for SkillRetrievalService."""

    @pytest.fixture
    def skills_store(self):
        """Create a store with sample skills."""
        store = SkillMemoryIndexStore()

        # Add web-research skill
        web_skill = Skill(
            metadata=SkillMetadata(
                skill_id="web-research",
                name="Web Research",
                version="1.0.0",
                description="Perform web research",
                team_id="research",
                tags=["research", "search", "web"],
            ),
            content=SkillContent(
                purpose="Extract web information",
                when_to_use="Need current data",
                how_to_apply="Search and browse",
                example="Research quantum computing",
            ),
        )
        store.index_skill(web_skill)

        # Add code-review skill
        code_skill = Skill(
            metadata=SkillMetadata(
                skill_id="code-review",
                name="Code Review",
                version="1.0.0",
                description="Review code",
                team_id="coding",
                tags=["coding", "review", "quality"],
            ),
            content=SkillContent(
                purpose="Review code",
                when_to_use="Before merging",
                how_to_apply="Check code",
                example="Review auth module",
            ),
        )
        store.index_skill(code_skill)

        return store

    def test_retrieve_for_task(self, skills_store):
        """Test retrieving skills for a task."""
        service = SkillRetrievalService(memory_store=skills_store)

        results = service.retrieve_for_task(
            task_description="I need to research quantum computing",
            available_skills=["web-research", "code-review"],
        )

        assert len(results) > 0
        # web-research should be more relevant for research tasks
        skill_ids = [r["skill_id"] for r in results]
        assert "web-research" in skill_ids

    def test_retrieve_for_coding_task(self, skills_store):
        """Test retrieving skills for a coding task."""
        service = SkillRetrievalService(memory_store=skills_store)

        results = service.retrieve_for_task(
            task_description="Review my code before merging",
            available_skills=["web-research", "code-review"],
        )

        skill_ids = [r["skill_id"] for r in results]
        assert "code-review" in skill_ids

    def test_retrieve_with_top_k_limit(self, skills_store):
        """Test retrieval with top_k limit."""
        service = SkillRetrievalService(memory_store=skills_store)

        results = service.retrieve_for_task(
            task_description="test task",
            top_k=1,
        )

        assert len(results) <= 1

    def test_get_similar_skills(self, skills_store):
        """Test finding similar skills."""
        service = SkillRetrievalService(memory_store=skills_store)

        similar = service.get_similar_skills("web-research")

        # Should not include the original skill
        skill_ids = [s["skill_id"] for s in similar]
        assert "web-research" not in skill_ids
