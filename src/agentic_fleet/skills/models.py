"""Skill data models for database storage and API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


# =============================================================================
# Hierarchical Context Organization (Agent Skills Specification)
# =============================================================================

class SkillType(str, Enum):
    """What the skill does - primary taxonomy classification."""

    OPERATIONAL = "operational"      # Does things (data, tools)
    COGNITIVE = "cognitive"          # Plans/reasons
    COMMUNICATION = "communication"  # Generates/synthesizes
    DOMAIN = "domain"                # Expertise-based


class SkillCategory(BaseModel):
    """Category within a skill type."""

    model_config = ConfigDict(extra="forbid")

    type: SkillType
    name: str = Field(..., description="Category name (e.g., 'data_processing')")
    description: str = Field(..., description="What this category encompasses")
    parent_categories: list[str] = Field(default_factory=list, description="Parent category path")


class SkillSpecialization(BaseModel):
    """Specific specialization within a category."""

    model_config = ConfigDict(extra="forbid")

    type: SkillType
    category: str
    name: str = Field(..., description="Specialization name (e.g., 'web-scraping')")
    description: str = Field(..., description="What this specialization covers")
    related_specializations: list[str] = Field(
        default_factory=list, description="Related specialization IDs"
    )


class SkillKnowledge(BaseModel):
    """Knowledge domain this skill operates in."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(..., description="Primary knowledge domain")
    subdomains: list[str] = Field(default_factory=list, description="Subdomain hierarchy")
    knowledge_graph_relations: list[dict[str, Any]] = Field(
        default_factory=list, description="Knowledge graph relations"
    )


class SkillRelationalContext(BaseModel):
    """How this skill relates to other skills."""

    model_config = ConfigDict(extra="forbid")

    depends_on: list[str] = Field(default_factory=list, description="Skill IDs this skill depends on")
    composes_with: list[str] = Field(
        default_factory=list, description="Skill IDs this skill can be combined with"
    )
    alternatives: list[str] = Field(
        default_factory=list, description="Alternative skill IDs"
    )
    supersedes: list[str] = Field(
        default_factory=list, description="Skill IDs this skill supersedes"
    )
    related_skills: list[str] = Field(
        default_factory=list, description="Related but not dependent skills"
    )


class HierarchicalSkillContext(BaseModel):
    """Complete hierarchical context for a skill."""

    model_config = ConfigDict(extra="forbid")

    # Taxonomy
    skill_id: str
    skill_type: SkillType
    category: str
    specialization: str

    # Knowledge organization
    knowledge: SkillKnowledge

    # Relational context
    relational: SkillRelationalContext

    # Memory system integration
    memory_keys: list[str] = Field(default_factory=list)
    embedding_keywords: list[str] = Field(default_factory=list)

    # Activation context
    trigger_patterns: list[str] = Field(default_factory=list)
    context_requirements: list[str] = Field(default_factory=list)


class SkillMemoryIndex(BaseModel):
    """Index structure for skill retrieval from memory."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str
    hierarchical_path: str = Field(
        ..., description="e.g., 'operational/data_processing/extraction/web-scraping'"
    )
    embedding_vector: list[float] | None = Field(
        default=None, description="Optional embedding for semantic search"
    )
    keywords: list[str] = Field(default_factory=list)
    capability_tags: list[str] = Field(default_factory=list)
    domain_tags: list[str] = Field(default_factory=list)

    # For retrieval
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    usage_count: int = 0
    success_rate: float = 0.0


# =============================================================================
# Core Skill Models
# =============================================================================


class SkillMetadata(BaseModel):
    """Metadata extracted from SKILL.md YAML frontmatter."""

    model_config = ConfigDict(extra="allow")

    skill_id: str = Field(..., description="Unique identifier for the skill")
    name: str = Field(..., description="Human-readable skill name")
    version: str = Field(default="1.0.0", description="Semantic version")
    description: str = Field(..., description="Brief skill description")
    team_id: str = Field(..., description="Team that owns this skill")
    tags: list[str] = Field(default_factory=list, description="Skill categorization tags")

    @field_validator("skill_id")
    @classmethod
    def _skill_id(cls, value: str) -> str:
        # Allow alphanumeric, hyphens, and underscores
        import re
        # Convert underscores to hyphens and lowercase
        value = value.lower().replace("_", "-")
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9-]*$", value):
            raise ValueError(f"skill_id must start with a letter and contain only alphanumeric characters and hyphens: {value}")
        return value

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: list[str]) -> list[str]:
        return [tag.lower().strip() for tag in value]


class SkillContent(BaseModel):
    """Full skill content including documentation."""

    model_config = ConfigDict(extra="forbid")

    purpose: str = Field(..., description="When and why to use this skill")
    when_to_use: str = Field(..., description="Conditions triggering skill selection")
    how_to_apply: str = Field(..., description="Implementation guidance")
    example: str = Field(default="", description="Usage example")
    constraints: list[str] = Field(default_factory=list, description="Skill-specific constraints")
    prerequisites: list[str] = Field(default_factory=list, description="Required context/tools")


class Skill(BaseModel):
    """Complete skill representation combining metadata and content."""

    model_config = ConfigDict(extra="allow")

    metadata: SkillMetadata
    content: SkillContent

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Skill":
        """Create Skill from dictionary (typically parsed from SKILL.md)."""
        return cls(
            metadata=SkillMetadata(**data["metadata"]),
            content=SkillContent(**data["content"]),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "metadata": self.metadata.model_dump(),
            "content": self.content.model_dump(),
        }


class SkillContext(BaseModel):
    """Extended context including mounted skills (extends TaskContext)."""

    model_config = ConfigDict(extra="forbid")

    team_id: str
    constraints: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    mounted_skills: list[str] = Field(default_factory=list, description="Skill IDs currently mounted")
    available_skills: list[Skill] = Field(
        default_factory=list, description="All available skills for team"
    )

    def add_skill(self, skill_id: str) -> None:
        """Mount a skill for this execution context."""
        if skill_id not in self.mounted_skills:
            self.mounted_skills.append(skill_id)

    def remove_skill(self, skill_id: str) -> None:
        """Unmount a skill from this execution context."""
        if skill_id in self.mounted_skills:
            self.mounted_skills.remove(skill_id)

    def has_skill(self, skill_id: str) -> bool:
        """Check if a skill is mounted."""
        return skill_id in self.mounted_skills

    def is_available(self, skill_id: str) -> bool:
        """Check if a skill is available."""
        return skill_id in self.available_skill_ids

    @property
    def available_skill_ids(self) -> list[str]:
        """Return available skill IDs derived from skill objects."""
        return [skill.metadata.skill_id for skill in self.available_skills]

    @property
    def mounted_skill_ids(self) -> list[str]:
        """Return mounted skill IDs."""
        return list(self.mounted_skills)


# Database Models (SQLModel)

class SkillRecord(SQLModel, table=True):
    """Persisted skill record in database."""

    id: int | None = SQLField(default=None, primary_key=True)
    skill_id: str = SQLField(index=True, unique=True)
    name: str
    version: str
    description: str
    team_id: str
    tags: str | None = SQLField(default=None)  # JSON serialized
    content_purpose: str
    content_when_to_use: str
    content_how_to_apply: str
    content_example: str = ""
    content_constraints: str | None = SQLField(default=None)  # JSON serialized
    content_prerequisites: str | None = SQLField(default=None)  # JSON serialized
    created_at: datetime = SQLField(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = SQLField(default_factory=lambda: datetime.utcnow())
    is_active: bool = SQLField(default=True)


class SkillUsageTrace(SQLModel, table=True):
    """Track skill usage patterns for GEPA learning."""

    id: int | None = SQLField(default=None, primary_key=True)
    created_at: datetime = SQLField(default_factory=lambda: datetime.utcnow())
    run_id: int | None = SQLField(default=None, foreign_key="runtrace.id")
    skill_id: str = SQLField(index=True)
    task_type: str = SQLField(index=True)
    was_successful: bool
    execution_time_ms: int
    team_id: str
