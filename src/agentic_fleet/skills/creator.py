"""Skill Creator DSPy signatures for LLM-based skill generation.

This module implements the 6-step skill creation workflow inspired by Anthropic's
skill-creator pattern (https://github.com/anthropics/skills), adapted for DSPy-based
LLM orchestration with hierarchical context organization.

Step 1: UNDERSTAND - Extract task context and requirements
Step 2: PLAN - Identify resources and skill structure
Step 3: INITIALIZE - Create skill skeleton
Step 4: EDIT - Generate full skill content
Step 5: PACKAGE - Validate and prepare for approval
Step 6: ITERATE - HITL approval workflow

Key Design Principles (Anthropic Pattern):
- Progressive Disclosure: Metadata -> SKILL.md body -> Bundled resources
- Degrees of Freedom: High (text) -> Medium (pseudocode) -> Low (scripts)
- Concise is Key: Challenge each piece of information
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

import dspy
from pydantic import BaseModel, Field

from agentic_fleet.skills.models import (
    HierarchicalSkillContext,
    SkillKnowledge,
    SkillRelationalContext,
    SkillType,
)


# =============================================================================
# ENUMS & CONSTANTS
# =============================================================================

class FreedomLevel(str, Enum):
    """Degrees of freedom for skill implementation."""

    HIGH = "high"      # Text-based instructions, context-dependent
    MEDIUM = "medium"  # Pseudocode or parameterized scripts
    LOW = "low"        # Specific scripts, few parameters


# =============================================================================
# Step 1: UNDERSTAND - Extract task context
# =============================================================================

class SkillUnderstandSignature(dspy.Signature):
    """Analyze task requirements and gather usage patterns.

    This step mirrors Anthropic's "Understanding with Concrete Examples" step.
    Key questions to answer:
    - What functionality should this skill support?
    - Can you give examples of how this skill would be used?
    - What would a user say that should trigger this skill?
    """

    raw_request: str = dspy.InputField(
        desc="Raw user request for a new skill"
    )
    context_history: str = dspy.InputField(
        desc="Relevant conversation/context history", default=""
    )

    # Outputs
    task_summary: str = dspy.OutputField(
        desc="Concise 2-3 sentence summary of what the skill should do"
    )
    trigger_patterns: str = dspy.OutputField(
        desc="Comma-separated phrases that would trigger this skill"
    )
    example_patterns: str = dspy.OutputField(
        desc="Comma-separated examples in format: user_request -> expected_output"
    )
    required_capabilities: str = dspy.OutputField(
        desc="Comma-separated tools/APIs/capabilities needed"
    )


# =============================================================================
# Step 2: PLAN - Identify resources and structure
# =============================================================================

class SkillPlanSignature(dspy.Signature):
    """Plan skill structure and identify reusable resources.

    This step mirrors Anthropic's "Planning Reusable Contents" step.
    - Map to hierarchical taxonomy (type/category/specialization)
    - Identify scripts/ references/ assets needed
    - Avoid duplication with existing skills
    """

    task_summary: str = dspy.InputField(desc="Summary from UNDERSTAND step")
    required_capabilities: str = dspy.InputField(desc="Required capabilities")
    existing_skills: str = dspy.InputField(
        desc="Comma-separated list of existing skill IDs to avoid duplication", default=""
    )

    # Outputs
    skill_taxonomy: str = dspy.OutputField(
        desc="Format: type/category/specialization (e.g., operational/research/web-research)"
    )
    freedom_level: str = dspy.OutputField(
        desc="One of: high, medium, low (see Anthropic degrees of freedom pattern)"
    )
    scripts_needed: str = dspy.OutputField(
        desc="Comma-separated script names (e.g., rotate.py, extract.sh)"
    )
    references_needed: str = dspy.OutputField(
        desc="Comma-separated reference document names (e.g., SCHEMAS.md, API.md)"
    )
    assets_needed: str = dspy.OutputField(
        desc="Comma-separated asset/template names (e.g., templates/config.yaml)"
    )
    avoid_duplication: str = dspy.OutputField(
        desc="Comma-separated existing skill IDs this would duplicate"
    )
    knowledge_domain: str = dspy.OutputField(
        desc="Primary knowledge domain (e.g., software, finance, web)"
    )


# =============================================================================
# Step 3: INITIALIZE - Create skill skeleton
# =============================================================================

class SkillInitializeSignature(dspy.Signature):
    """Create initial skill structure from plan.

    This step mirrors Anthropic's "Initializing the Skill" step.
    Creates:
    - Skill directory structure
    - SKILL.md template with frontmatter
    - scripts/, references/, assets/ directories
    - Example files
    """

    skill_name: str = dspy.InputField(
        desc="Validated skill name (lowercase with hyphens)"
    )
    skill_taxonomy: str = dspy.InputField(
        desc="Type/category/specialization path"
    )
    task_summary: str = dspy.InputField(desc="Task summary")
    freedom_level: str = dspy.InputField(
        desc="Freedom level: high/medium/low"
    )

    # Outputs
    skill_directory: str = dspy.OutputField(
        desc="Path where skill will be created"
    )
    skill_yaml: str = dspy.OutputField(
        desc="Complete YAML frontmatter for SKILL.md with hierarchical context"
    )
    script_templates: str = dspy.OutputField(
        desc="JSON array of {name, content} for scripts to create"
    )
    reference_templates: str = dspy.OutputField(
        desc="JSON array of {name, content} for reference docs"
    )
    asset_templates: str = dspy.OutputField(
        desc="JSON array of {name, content} for assets"
    )
    directory_structure: str = dspy.OutputField(
        desc="Tree representation of skill directory"
    )


# =============================================================================
# Step 4: EDIT - Generate full skill content
# =============================================================================

class SkillEditSignature(dspy.Signature):
    """Generate full skill content including documentation and implementation.

    This step mirrors Anthropic's "Edit the Skill" step.
    - Apply progressive disclosure design
    - Define degrees of freedom in instructions
    - Create comprehensive SKILL.md content
    """

    skill_name: str = dspy.InputField(desc="Skill name")
    task_summary: str = dspy.InputField(desc="Task summary")
    example_patterns: str = dspy.InputField(
        desc="Comma-separated usage examples"
    )
    required_capabilities: str = dspy.InputField(
        desc="Comma-separated required tools/capabilities"
    )
    compatibility_notes: str = dspy.InputField(
        desc="Environment/dependency requirements", default=""
    )
    freedom_level: str = dspy.InputField(
        desc="Freedom level: high/medium/low"
    )

    # Progressive Disclosure Outputs
    skill_purpose: str = dspy.OutputField(
        desc="When and why to use this skill (Level 2)"
    )
    when_to_use: str = dspy.OutputField(
        desc="Conditions/triggers for selecting this skill (Level 2)"
    )
    how_to_apply: str = dspy.OutputField(
        desc="Step-by-step instructions with appropriate freedom (Level 2)"
    )
    example: str = dspy.OutputField(desc="Concrete usage example (Level 2)")
    constraints: str = dspy.OutputField(
        desc="Comma-separated skill-specific constraints (Level 2)"
    )
    prerequisites: str = dspy.OutputField(
        desc="Comma-separated required context/tools (Level 2)"
    )
    reference_links: str = dspy.OutputField(
        desc="JSON of {name: url/path} for bundled references (Level 3)"
    )


# =============================================================================
# Step 5: PACKAGE - Validate and finalize
# =============================================================================

class SkillPackageSignature(dspy.Signature):
    """Validate skill and prepare for approval.

    This step mirrors Anthropic's "Packaging a Skill" step.
    Validation checks:
    - YAML frontmatter format and required fields
    - Skill naming conventions and directory structure
    - Description completeness and quality
    - File organization and resource references
    """

    skill_path: str = dspy.InputField(desc="Path to skill directory")
    skill_content: str = dspy.InputField(desc="Full SKILL.md content")
    skill_yaml: str = dspy.InputField(desc="YAML frontmatter")
    directory_structure: str = dspy.InputField(desc="Directory tree")

    # Outputs
    validation_results: str = dspy.OutputField(
        desc="JSON array of {level: error/warning/info, message: string}"
    )
    quality_score: str = dspy.OutputField(
        desc="Skill quality score from 1-10 with brief justification"
    )
    improvement_suggestions: str = dspy.OutputField(
        desc="JSON array of {area: string, suggestion: string, priority: high/medium/low}"
    )
    package_status: str = dspy.OutputField(
        desc="One of: ready_for_review, needs_revision, incomplete"
    )


# =============================================================================
# Step 6: ITERATE - HITL approval workflow
# =============================================================================

class SkillApprovalRequest(BaseModel):
    """HITL approval request for skill creation.

    Based on Anthropic's iterative skill development process.
    """

    skill_name: str
    skill_description: str
    skill_yaml: str
    skill_instructions: str
    quality_score: float
    validation_results: list[dict[str, Any]]
    improvement_suggestions: list[dict[str, Any]]
    freedom_level: str
    knowledge_domain: str
    created_by: str = "llm"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SkillApprovalSignature(dspy.Signature):
    """Human review decision for skill creation.

    This step implements the HITL workflow where humans review
    and approve skills before deployment.
    """

    approval_request: str = dspy.InputField(
        desc="Serialized SkillApprovalRequest JSON"
    )
    human_feedback: str = dspy.InputField(
        desc="Human feedback if rejected or requesting changes", default=""
    )

    # Outputs
    approval_status: str = dspy.OutputField(
        desc="One of: approved, rejected, revision_requested"
    )
    approved_skill_yaml: str = dspy.OutputField(
        desc="Final approved YAML frontmatter"
    )
    approved_skill_content: str = dspy.OutputField(
        desc="Final approved markdown content"
    )
    revision_notes: str = dspy.OutputField(
        desc="JSON of {section: string, instruction: string} if revision_requested"
    )


# =============================================================================
# Skill Creator Workflow Orchestrator (Combined)
# =============================================================================

class SkillCreatorSignature(dspy.Signature):
    """Generate a new skill based on task requirements and usage examples.

    This is the main orchestrator signature that combines all 6 steps
    into a single DSPy call for quick skill generation.
    """

    task_description: str = dspy.InputField(
        desc="Description of the task to create a skill for"
    )
    usage_examples: str = dspy.InputField(
        desc="Concrete examples of how the skill should be used", default=""
    )
    available_tools: str = dspy.InputField(
        desc="List of available tools and their capabilities", default=""
    )
    existing_skills: str = dspy.InputField(
        desc="List of existing skill IDs to avoid duplication", default=""
    )

    # Outputs - Combined from all steps
    skill_name: str = dspy.OutputField(
        desc="Proposed skill name (lowercase with hyphens)"
    )
    skill_description: str = dspy.OutputField(
        desc="What the skill does AND specific triggers for when to use it"
    )
    skill_yaml: str = dspy.OutputField(
        desc="Complete YAML frontmatter with hierarchical context"
    )
    skill_taxonomy: str = dspy.OutputField(
        desc="Type/category/specialization path"
    )
    skill_instructions: str = dspy.OutputField(
        desc="Full markdown instructions with progressive disclosure"
    )
    freedom_level: str = dspy.OutputField(
        desc="One of: high, medium, low"
    )
    suggested_tools: str = dspy.OutputField(
        desc="Tools the skill should use"
    )
    compatibility_notes: str = dspy.OutputField(
        desc="Environment/dependency requirements"
    )
    scripts_needed: str = dspy.OutputField(
        desc="JSON array of {name, purpose} for scripts"
    )
    references_needed: str = dspy.OutputField(
        desc="JSON array of {name, purpose} for reference docs"
    )


# =============================================================================
# Skill Retrieval from Memory
# =============================================================================

class SkillRetrievalSignature(dspy.Signature):
    """Retrieve relevant skills from memory based on current task.

    Uses hierarchical path, keywords, and embeddings for retrieval.
    """

    task_description: str = dspy.InputField(
        desc="Current task to find skills for"
    )
    available_skills: str = dspy.InputField(
        desc="Comma-separated list of available skill IDs"
    )
    memory_index: str = dspy.InputField(
        desc="Serialized skill memory index (JSON)", default=""
    )

    relevant_skills: str = dspy.OutputField(
        desc="Comma-separated relevant skill IDs"
    )
    retrieval_reasoning: str = dspy.OutputField(
        desc="Why each skill is relevant (one line per skill)"
    )
    suggested_mount_order: str = dspy.OutputField(
        desc="Comma-separated skill IDs in order to mount"
    )


# =============================================================================
# Helper Functions
# =============================================================================

def create_hierarchical_context(
    skill_id: str,
    taxonomy: str,
    trigger_patterns: list[str],
    context_requirements: list[str],
    depends_on: list[str] | None = None,
    composes_with: list[str] | None = None,
    alternatives: list[str] | None = None,
    domain: str = "general",
    subdomains: list[str] | None = None,
) -> HierarchicalSkillContext:
    """Create a HierarchicalSkillContext from parsed taxonomy.

    Args:
        skill_id: The skill identifier
        taxonomy: Type/category/specialization path
        trigger_patterns: When this skill should be invoked
        context_requirements: Required context for this skill
        depends_on: Skills this depends on
        composes_with: Skills this can combine with
        alternatives: Alternative skills
        domain: Primary knowledge domain
        subdomains: Subdomain hierarchy

    Returns:
        HierarchicalSkillContext instance
    """
    parts = taxonomy.split("/")
    if len(parts) >= 3:
        skill_type = SkillType(parts[0])
        category = parts[1]
        specialization = parts[2]
    else:
        skill_type = SkillType.OPERATIONAL
        category = parts[1] if len(parts) > 1 else "general"
        specialization = parts[-1] if parts else skill_id

    knowledge = SkillKnowledge(
        domain=domain,
        subdomains=subdomains or [],
        knowledge_graph_relations=[],
    )

    relational = SkillRelationalContext(
        depends_on=depends_on or [],
        composes_with=composes_with or [],
        alternatives=alternatives or [],
        supersedes=[],
        related_skills=[],
    )

    return HierarchicalSkillContext(
        skill_id=skill_id,
        skill_type=skill_type,
        category=category,
        specialization=specialization,
        knowledge=knowledge,
        relational=relational,
        memory_keys=[skill_id, specialization, category],
        embedding_keywords=trigger_patterns,
        trigger_patterns=trigger_patterns,
        context_requirements=context_requirements,
    )


def parse_skill_taxonomy(taxonomy: str) -> dict[str, str]:
    """Parse a taxonomy string into components.

    Args:
        taxonomy: String in format "type/category/specialization"

    Returns:
        Dictionary with type, category, and specialization keys
    """
    parts = taxonomy.split("/")
    return {
        "type": parts[0] if len(parts) > 0 else "operational",
        "category": parts[1] if len(parts) > 1 else "general",
        "specialization": parts[2] if len(parts) > 2 else parts[-1] if parts else "",
    }


def generate_skill_yaml(
    skill_id: str,
    name: str,
    description: str,
    team_id: str,
    tags: list[str],
    taxonomy: str,
    knowledge_domain: str,
    subdomains: list[str],
    trigger_patterns: list[str],
    context_requirements: list[str],
    depends_on: list[str] | None = None,
    composes_with: list[str] | None = None,
    alternatives: list[str] | None = None,
    version: str = "1.0.0",
) -> str:
    """Generate YAML frontmatter for SKILL.md.

    Args:
        skill_id: Unique skill identifier
        name: Human-readable name
        description: What the skill does AND when to use it
        team_id: Team that owns this skill
        tags: Skill categorization tags
        taxonomy: Type/category/specialization path
        knowledge_domain: Primary knowledge domain
        subdomains: Subdomain hierarchy
        trigger_patterns: When this skill should be invoked
        context_requirements: Required context/tools
        depends_on: Skills this depends on
        composes_with: Skills this can combine with
        alternatives: Alternative skills
        version: Semantic version

    Returns:
        YAML frontmatter string
    """
    parts = taxonomy.split("/")
    skill_type = parts[0] if len(parts) > 0 else "operational"
    category = parts[1] if len(parts) > 1 else "general"
    specialization = parts[2] if len(parts) > 2 else parts[-1] if parts else skill_id

    yaml = f"""---
# Agent Skills Specification v1.0
skill_id: {skill_id}
name: {name}
version: {version}
description: {description}
team_id: {team_id}
tags: [{', '.join(tags)}]

# Hierarchical Context (Agent Skills Specification)
type: {skill_type}
category: {category}
specialization: {specialization}

# Knowledge Organization
knowledge:
  domain: {knowledge_domain}
  subdomains: [{', '.join(subdomains) if subdomains else ''}]
  knowledge_graph_relations: []

# Relational Context
relational:
  depends_on: [{', '.join(depends_on) if depends_on else ''}]
  composes_with: [{', '.join(composes_with) if composes_with else ''}]
  alternatives: [{', '.join(alternatives) if alternatives else ''}]
  related_skills: []

# Memory System Integration
memory_keys: [{skill_id}, {specialization}, {category}]
embedding_keywords: [{', '.join(trigger_patterns[:5])}]

# Activation Context
trigger_patterns:
{chr(10).join(f'  - "{pattern}"' for pattern in trigger_patterns[:10])}

context_requirements:
{chr(10).join(f'  - {req}' for req in context_requirements)}
---"""
    return yaml


def generate_directory_structure(
    skill_name: str,
    scripts: list[str],
    references: list[str],
    assets: list[str],
) -> str:
    """Generate directory structure tree.

    Args:
        skill_name: Name of the skill
        scripts: List of script names
        references: List of reference document names
        assets: List of asset names

    Returns:
        Directory tree string
    """
    lines = [f"{skill_name}/", "├── SKILL.md"]

    if scripts:
        lines.append("├── scripts/")
        for script in scripts:
            lines.append(f"│   ├── {script}")

    if references:
        lines.append("├── references/")
        for ref in references:
            lines.append(f"│   ├── {ref}")

    if assets:
        lines.append("├── assets/")
        for asset in assets:
            lines.append(f"│   ├── {asset}")

    return "\n".join(lines)
