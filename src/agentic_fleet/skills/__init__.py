"""Skill Mount feature for continual learning and knowledge management.

This module provides:
- Skill data models (Skill, SkillMetadata, SkillContent, SkillContext)
- Hierarchical context organization (SkillType, SkillCategory, SkillSpecialization)
- Skill creation via DSPy signatures
- HITL approval workflow
- Memory system integration for skill retrieval
- Repository for file I/O
- Manager for CRUD operations
"""

from agentic_fleet.skills.approval import (
    ApprovalDecision,
    ApprovalStatus,
    ApprovalStore,
    SkillApprovalWorkflow,
    approval_store,
)
from agentic_fleet.skills.creator import (
    SkillApprovalRequest,
    SkillApprovalSignature,
    SkillApprovalSignature as SkillCreatorSignature,
    SkillEditSignature,
    SkillInitializeSignature,
    SkillPackageSignature,
    SkillPlanSignature,
    SkillUnderstandSignature,
    SkillRetrievalSignature,
    create_hierarchical_context,
    parse_skill_taxonomy,
)
from agentic_fleet.skills.memory import (
    SkillMemoryIndex,
    SkillMemoryIndexStore,
    SkillRetrievalService,
    skill_memory_store,
    skill_retrieval_service,
)
from agentic_fleet.skills.models import (
    HierarchicalSkillContext,
    Skill,
    SkillCategory,
    SkillContent,
    SkillContext,
    SkillKnowledge,
    SkillRelationalContext,
    SkillSpecialization,
    SkillMetadata,
    SkillRecord,
    SkillType,
    SkillUsageTrace,
)
from agentic_fleet.skills.repository import SkillMount, load_skill, load_team_skills
from agentic_fleet.skills.manager import SkillManager

__all__ = [
    # Models
    "Skill",
    "SkillContent",
    "SkillContext",
    "SkillMetadata",
    "SkillRecord",
    "SkillUsageTrace",
    # Hierarchical Context
    "SkillType",
    "SkillCategory",
    "SkillSpecialization",
    "SkillKnowledge",
    "SkillRelationalContext",
    "HierarchicalSkillContext",
    "SkillMemoryIndex",
    # Repository & Manager
    "SkillMount",
    "SkillManager",
    "load_skill",
    "load_team_skills",
    # Creator
    "SkillUnderstandSignature",
    "SkillPlanSignature",
    "SkillInitializeSignature",
    "SkillEditSignature",
    "SkillPackageSignature",
    "SkillApprovalSignature",
    "SkillApprovalRequest",
    "SkillCreatorSignature",
    "SkillRetrievalSignature",
    "create_hierarchical_context",
    "parse_skill_taxonomy",
    # Approval Workflow
    "ApprovalStatus",
    "ApprovalDecision",
    "SkillApprovalWorkflow",
    "ApprovalStore",
    "approval_store",
    # Memory Integration
    "SkillMemoryIndexStore",
    "SkillRetrievalService",
    "skill_memory_store",
    "skill_retrieval_service",
]
