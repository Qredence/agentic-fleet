"""Memory system integration for skill retrieval and indexing.

This module provides functionality to:
- Index skills in memory for semantic retrieval
- Retrieve relevant skills based on task descriptions
- Track skill usage patterns for learning
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agentic_fleet.skills.models import (
    HierarchicalSkillContext,
    Skill,
    SkillMemoryIndex,
    SkillType,
)


class SkillMemoryIndexStore:
    """In-memory store for skill memory indexes.

    In production, this would integrate with a vector database
    like Pinecone, Weaviate, or Qdrant for semantic search.
    """

    def __init__(self):
        self._indexes: dict[str, SkillMemoryIndex] = {}
        self._skill_contexts: dict[str, HierarchicalSkillContext] = {}

    def index_skill(
        self,
        skill: Skill,
        hierarchical_path: str | None = None,
        embedding_vector: list[float] | None = None,
    ) -> SkillMemoryIndex:
        """Index a skill for retrieval.

        Args:
            skill: The skill to index
            hierarchical_path: Optional explicit path (auto-generated if not provided)
            embedding_vector: Optional embedding vector for semantic search

        Returns:
            The created SkillMemoryIndex
        """
        if hierarchical_path is None:
            hierarchical_path = self._infer_hierarchical_path(skill)

        keywords = self._extract_keywords(skill)
        capability_tags = self._extract_capability_tags(skill)
        domain_tags = self._extract_domain_tags(skill)

        index = SkillMemoryIndex(
            skill_id=skill.metadata.skill_id,
            hierarchical_path=hierarchical_path,
            embedding_vector=embedding_vector,
            keywords=keywords,
            capability_tags=capability_tags,
            domain_tags=domain_tags,
        )

        self._indexes[skill.metadata.skill_id] = index
        return index

    def get_index(self, skill_id: str) -> SkillMemoryIndex | None:
        """Get the memory index for a skill."""
        return self._indexes.get(skill_id)

    def update_usage(
        self,
        skill_id: str,
        successful: bool,
        execution_time_ms: int | None = None,
    ) -> bool:
        """Update usage statistics for a skill.

        Args:
            skill_id: The skill that was used
            successful: Whether the skill execution was successful
            execution_time_ms: Optional execution time

        Returns:
            True if updated, False if skill not found
        """
        index = self._indexes.get(skill_id)
        if index is None:
            return False

        index.last_accessed = datetime.utcnow()
        index.usage_count += 1

        if execution_time_ms is not None:
            # Update running success rate
            if hasattr(index, "success_rate"):
                old_rate = index.success_rate
                if old_rate == 0:
                    index.success_rate = 1.0 if successful else 0.0
                else:
                    # Simple moving average
                    index.success_rate = (old_rate * 0.9) + (1.0 if successful else 0.0) * 0.1

        return True

    def search_by_keyword(self, keywords: list[str]) -> list[SkillMemoryIndex]:
        """Search for skills matching any of the keywords."""
        results = []
        for index in self._indexes.values():
            index_keywords = set(kw.lower() for kw in index.keywords)
            query_set = set(kw.lower() for kw in keywords)
            if index_keywords & query_set:
                results.append(index)
        return results

    def search_by_hierarchy(
        self,
        skill_type: SkillType | None = None,
        category: str | None = None,
        specialization: str | None = None,
    ) -> list[SkillMemoryIndex]:
        """Search for skills in a specific hierarchy level."""
        results = []
        for index in self._indexes.values():
            path_parts = index.hierarchical_path.split("/")
            if len(path_parts) >= 3:
                index_type, index_category, index_specialization = path_parts[:3]

                if skill_type is not None and index_type != skill_type.value:
                    continue
                if category is not None and index_category != category:
                    continue
                if specialization is not None and index_specialization != specialization:
                    continue

                results.append(index)
        return results

    def search_by_capability(self, capability: str) -> list[SkillMemoryIndex]:
        """Search for skills with a specific capability tag."""
        results = []
        for index in self._indexes.values():
            if capability.lower() in [t.lower() for t in index.capability_tags]:
                results.append(index)
        return results

    def list_all(self) -> list[SkillMemoryIndex]:
        """List all indexed skills."""
        return list(self._indexes.values())

    def serialize_indexes(self) -> str:
        """Serialize all indexes to JSON."""
        return json.dumps(
            {
                skill_id: index.model_dump()
                for skill_id, index in self._indexes.items()
            },
            indent=2,
            default=str,
        )

    def deserialize_indexes(self, data: str) -> None:
        """Deserialize indexes from JSON."""
        parsed = json.loads(data)
        for skill_id, index_data in parsed.items():
            self._indexes[skill_id] = SkillMemoryIndex(**index_data)

    def _infer_hierarchical_path(self, skill: Skill) -> str:
        """Infer hierarchical path from skill metadata.

        Default mapping based on tags and team_id.
        """
        skill_id = skill.metadata.skill_id
        tags = skill.metadata.tags
        team_id = skill.metadata.team_id

        # Default path based on team_id as category
        skill_type = "operational"  # Default type
        category = team_id
        specialization = skill_id

        # Adjust based on tags
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in ["reasoning", "planning", "analysis"]:
                skill_type = "cognitive"
            elif tag_lower in ["generation", "writing", "synthesis"]:
                skill_type = "communication"
            elif tag_lower in ["domain", "expertise", "specialized"]:
                skill_type = "domain"
            elif tag_lower in ["extraction", "processing", "loading"]:
                category = "data_processing"
            elif tag_lower in ["research", "search", "discovery"]:
                category = "research"
            elif tag_lower in ["coding", "development", "programming"]:
                category = "software_development"

        return f"{skill_type}/{category}/{specialization}"

    def _extract_keywords(self, skill: Skill) -> list[str]:
        """Extract search keywords from a skill."""
        keywords = [
            skill.metadata.skill_id,
            skill.metadata.name.lower(),
            skill.metadata.description.lower(),
            skill.metadata.team_id,
        ]
        keywords.extend(skill.metadata.tags)
        keywords.extend(skill.content.purpose.lower().split()[:10])
        return list(set(keywords))

    def _extract_capability_tags(self, skill: Skill) -> list[str]:
        """Extract capability tags from a skill."""
        tags = list(skill.metadata.tags)

        # Add inferred capabilities from content
        purpose = skill.content.purpose.lower()
        if "search" in purpose or "research" in purpose:
            tags.append("search")
        if "extract" in purpose or "scrape" in purpose:
            tags.append("extraction")
        if "analyze" in purpose or "analyse" in purpose:
            tags.append("analysis")
        if "generate" in purpose or "write" in purpose:
            tags.append("generation")
        if "plan" in purpose or "reason" in purpose:
            tags.append("reasoning")

        return list(set(tags))

    def _extract_domain_tags(self, skill: Skill) -> list[str]:
        """Extract domain tags from a skill."""
        domains = [skill.metadata.team_id]

        # Add inferred domains from content
        purpose = skill.content.purpose.lower()
        if "web" in purpose or "internet" in purpose:
            domains.append("web")
        if "code" in purpose or "programming" in purpose:
            domains.append("software")
        if "data" in purpose or "analytics" in purpose:
            domains.append("data")
        if "business" in purpose or "finance" in purpose:
            domains.append("business")
        if "science" in purpose or "research" in purpose:
            domains.append("science")

        return list(set(domains))


# Global memory index store instance
skill_memory_store = SkillMemoryIndexStore()


# =============================================================================
# Skill Retrieval Service
# =============================================================================

class SkillRetrievalService:
    """Service for retrieving relevant skills based on task context."""

    def __init__(self, memory_store: SkillMemoryIndexStore | None = None):
        self.memory_store = memory_store or skill_memory_store

    def retrieve_for_task(
        self,
        task_description: str,
        task_type: str | None = None,
        available_skills: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve the most relevant skills for a task.

        Args:
            task_description: Description of the current task
            task_type: Optional task type hint
            available_skills: Optional list of skill IDs to filter to
            top_k: Maximum number of skills to return

        Returns:
            List of skill info dicts sorted by relevance
        """
        # Extract keywords from task
        task_keywords = self._extract_task_keywords(task_description)

        # Search by keyword
        matching_indexes = self.memory_store.search_by_keyword(task_keywords)

        # Filter to available skills if specified
        if available_skills:
            available_set = set(available_skills)
            matching_indexes = [i for i in matching_indexes if i.skill_id in available_set]

        # Score and rank results
        scored_results = []
        for index in matching_indexes:
            score = self._calculate_relevance_score(task_description, index, task_type)
            scored_results.append({
                "skill_id": index.skill_id,
                "hierarchical_path": index.hierarchical_path,
                "score": score,
                "keywords": index.keywords,
                "capability_tags": index.capability_tags,
                "usage_count": index.usage_count,
                "success_rate": index.success_rate,
            })

        # Sort by score (descending) and take top_k
        scored_results.sort(key=lambda x: (-x["score"], -x["usage_count"]))
        return scored_results[:top_k]

    def get_similar_skills(
        self,
        skill_id: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Find skills similar to a given skill.

        Args:
            skill_id: The skill to find similar skills for
            top_k: Maximum number of similar skills to return

        Returns:
            List of similar skill info dicts
        """
        index = self.memory_store.get_index(skill_id)
        if index is None:
            return []

        # Find by capability tags
        similar = self.memory_store.search_by_capability("")
        # Filter out the original skill and score by shared tags
        results = []
        for other in similar:
            if other.skill_id == skill_id:
                continue
            other_index = self.memory_store.get_index(other.skill_id)
            if other_index is None:
                continue

            # Calculate tag overlap
            shared_tags = set(index.capability_tags) & set(other_index.capability_tags)
            score = len(shared_tags) / max(len(index.capability_tags), 1)

            if score > 0:
                results.append({
                    "skill_id": other.skill_id,
                    "hierarchical_path": other.hierarchical_path,
                    "score": score,
                    "shared_capabilities": list(shared_tags),
                })

        results.sort(key=lambda x: -x["score"])
        return results[:top_k]

    def _extract_task_keywords(self, task_description: str) -> list[str]:
        """Extract keywords from a task description."""
        # Simple keyword extraction
        words = task_description.lower().split()
        # Filter out common words
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "for", "on"}
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return keywords

    def _calculate_relevance_score(
        self,
        task_description: str,
        index: SkillMemoryIndex,
        task_type: str | None = None,
    ) -> float:
        """Calculate a relevance score for a skill given a task."""
        score = 0.0
        task_lower = task_description.lower()

        # Keyword matching
        for keyword in index.keywords:
            if keyword.lower() in task_lower:
                score += 0.1

        # Capability tag matching
        for tag in index.capability_tags:
            if tag.lower() in task_lower:
                score += 0.2

        # Domain tag matching
        for domain in index.domain_tags:
            if domain.lower() in task_lower:
                score += 0.15

        # Hierarchy matching
        path_parts = index.hierarchical_path.split("/")
        for part in path_parts:
            if part.lower() in task_lower:
                score += 0.25

        # Task type hint bonus
        if task_type:
            for tag in index.capability_tags:
                if task_type.lower() in tag.lower():
                    score += 0.3

        # Normalize by number of keywords (avoid long skill lists dominating)
        max_possible = len(index.keywords) * 0.1 + len(index.capability_tags) * 0.2
        if max_possible > 0:
            score = min(score / max_possible, 1.0)

        return score


# Global retrieval service instance
skill_retrieval_service = SkillRetrievalService()
