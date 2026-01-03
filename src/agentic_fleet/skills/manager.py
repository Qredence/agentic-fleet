"""Skill management API for CRUD operations."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from sqlmodel import Session, select

from agentic_fleet.db import get_engine
from agentic_fleet.skills.models import (
    Skill,
    SkillMetadata,
    SkillRecord,
    SkillUsageTrace,
)
from agentic_fleet.skills.repository import (
    SKILLS_BASE_PATH,
    load_skill,
    list_team_skills,
)


class SkillManager:
    """Manage skills in file storage and database."""

    def __init__(self):
        """Initialize skill manager and ensure base path exists."""
        SKILLS_BASE_PATH.mkdir(parents=True, exist_ok=True)

    # File-based operations

    def create_skill(self, skill: Skill, team_id: str | None = None) -> Path:
        """Create a SKILL.md file from a Skill object.

        Args:
            skill: The Skill to create
            team_id: Team ID (defaults to skill.metadata.team_id)

        Returns:
            Path to created SKILL.md file
        """
        team = team_id or skill.metadata.team_id
        skill_dir = SKILLS_BASE_PATH / team / skill.metadata.skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_path = skill_dir / "SKILL.md"
        content = self._skill_to_markdown(skill)
        skill_path.write_text(content)

        return skill_path

    def get_skill(self, skill_id: str, team_id: str | None = None) -> Skill | None:
        """Load a skill from file storage.

        Args:
            skill_id: The skill identifier
            team_id: Optional team ID (defaults to "default")

        Returns:
            Skill object if found, None otherwise
        """
        return load_skill(skill_id, team_id)

    def list_skills(self, team_id: str | None = None) -> list[SkillMetadata]:
        """List all skills for a team.

        Args:
            team_id: Optional team ID (defaults to "default")

        Returns:
            List of SkillMetadata for all skills in the team
        """
        resolved_team = team_id or "default"
        skill_ids = list_team_skills(resolved_team)
        metadata_list: list[SkillMetadata] = []

        for skill_id in skill_ids:
            skill = self.get_skill(skill_id, resolved_team)
            if skill:
                metadata_list.append(skill.metadata)

        return metadata_list

    def update_skill(
        self,
        skill_id: str,
        updates: dict[str, Any],
        team_id: str | None = None,
    ) -> bool:
        """Update a skill file with new values.

        Args:
            skill_id: The skill identifier to update
            updates: Dictionary with "metadata" and/or "content" updates
            team_id: Optional team ID (defaults to "default")

        Returns:
            True if skill was updated, False if not found
        """
        skill = self.get_skill(skill_id, team_id)
        if not skill:
            return False

        # Update metadata
        for key, value in updates.get("metadata", {}).items():
            if hasattr(skill.metadata, key):
                setattr(skill.metadata, key, value)

        # Update content
        for key, value in updates.get("content", {}).items():
            if hasattr(skill.content, key):
                setattr(skill.content, key, value)

        # Rewrite file
        self.create_skill(skill, team_id)
        return True

    def delete_skill(self, skill_id: str, team_id: str | None = None) -> bool:
        """Delete a skill directory.

        Args:
            skill_id: The skill identifier to delete
            team_id: Optional team ID (defaults to "default")

        Returns:
            True if skill was deleted, False if not found
        """
        team = team_id or "default"
        skill_dir = SKILLS_BASE_PATH / team / skill_id

        if not skill_dir.exists():
            return False

        shutil.rmtree(skill_dir)
        return True

    # Database operations

    def save_skill_to_db(self, skill: Skill) -> SkillRecord:
        """Persist a skill to the database.

        Args:
            skill: The Skill to persist

        Returns:
            The created or updated SkillRecord
        """
        with Session(get_engine()) as session:
            # Check for existing skill
            existing = session.exec(
                select(SkillRecord).where(SkillRecord.skill_id == skill.metadata.skill_id)
            ).first()

            if existing:
                # Update existing
                existing.name = skill.metadata.name
                existing.version = skill.metadata.version
                existing.description = skill.metadata.description
                existing.team_id = skill.metadata.team_id
                existing.tags = json.dumps(skill.metadata.tags)
                existing.content_purpose = skill.content.purpose
                existing.content_when_to_use = skill.content.when_to_use
                existing.content_how_to_apply = skill.content.how_to_apply
                existing.content_example = skill.content.example
                existing.content_constraints = json.dumps(skill.content.constraints)
                existing.content_prerequisites = json.dumps(skill.content.prerequisites)
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing

            # Create new
            record = SkillRecord(
                skill_id=skill.metadata.skill_id,
                name=skill.metadata.name,
                version=skill.metadata.version,
                description=skill.metadata.description,
                team_id=skill.metadata.team_id,
                tags=json.dumps(skill.metadata.tags),
                content_purpose=skill.content.purpose,
                content_when_to_use=skill.content.when_to_use,
                content_how_to_apply=skill.content.how_to_apply,
                content_example=skill.content.example,
                content_constraints=json.dumps(skill.content.constraints),
                content_prerequisites=json.dumps(skill.content.prerequisites),
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def get_skill_from_db(self, skill_id: str) -> SkillRecord | None:
        """Retrieve a skill from the database.

        Args:
            skill_id: The skill identifier

        Returns:
            SkillRecord if found, None otherwise
        """
        with Session(get_engine()) as session:
            return session.exec(
                select(SkillRecord).where(SkillRecord.skill_id == skill_id)
            ).first()

    def get_skills_from_db(
        self,
        team_id: str | None = None,
        active_only: bool = True,
    ) -> list[SkillRecord]:
        """Get all skills from database, optionally filtered by team.

        Args:
            team_id: Optional team ID filter
            active_only: If True, only return active skills

        Returns:
            List of SkillRecord objects
        """
        with Session(get_engine()) as session:
            query = select(SkillRecord)
            if team_id:
                query = query.where(SkillRecord.team_id == team_id)
            if active_only:
                query = query.where(SkillRecord.is_active == True)
            return list(session.exec(query).all())

    def record_skill_usage(
        self,
        skill_id: str,
        task_type: str,
        was_successful: bool,
        execution_time_ms: int,
        team_id: str,
        run_id: int | None = None,
    ) -> SkillUsageTrace:
        """Record skill usage for GEPA learning.

        Args:
            skill_id: The skill identifier
            task_type: Type of task (e.g., "research", "coding")
            was_successful: Whether the skill usage was successful
            execution_time_ms: Execution time in milliseconds
            team_id: The team identifier
            run_id: Optional run trace ID

        Returns:
            The created SkillUsageTrace
        """
        with Session(get_engine()) as session:
            trace = SkillUsageTrace(
                skill_id=skill_id,
                task_type=task_type,
                was_successful=was_successful,
                execution_time_ms=execution_time_ms,
                team_id=team_id,
                run_id=run_id,
            )
            session.add(trace)
            session.commit()
            session.refresh(trace)
            return trace

    def get_successful_patterns(
        self,
        skill_id: str,
        min_count: int = 3,
    ) -> list[dict[str, Any]]:
        """Extract successful usage patterns for skill improvement.

        Args:
            skill_id: The skill identifier
            min_count: Minimum number of occurrences to include

        Returns:
            List of usage pattern dictionaries
        """
        with Session(get_engine()) as session:
            traces = session.exec(
                select(SkillUsageTrace).where(
                    SkillUsageTrace.skill_id == skill_id,
                    SkillUsageTrace.was_successful == True,
                )
            ).all()

            # Group by task type and calculate stats
            patterns: dict[str, dict[str, Any]] = {}
            for trace in traces:
                if trace.task_type not in patterns:
                    patterns[trace.task_type] = {
                        "task_type": trace.task_type,
                        "count": 0,
                        "total_time_ms": 0,
                    }
                patterns[trace.task_type]["count"] += 1
                patterns[trace.task_type]["total_time_ms"] += trace.execution_time_ms

            # Calculate averages and filter
            result = []
            for task_type, data in patterns.items():
                if data["count"] >= min_count:
                    result.append({
                        "task_type": task_type,
                        "count": data["count"],
                        "avg_time_ms": data["total_time_ms"] // data["count"],
                    })

            return result

    # Helper methods

    @staticmethod
    def _parse_json_field(value: str | None) -> list[str]:
        """Parse a JSON string field into a list."""
        if not value:
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
            return []
        except (json.JSONDecodeError, TypeError):
            return []

    def _skill_to_markdown(self, skill: Skill) -> str:
        """Convert a Skill object to SKILL.md format.

        Args:
            skill: The Skill to convert

        Returns:
            Markdown content for SKILL.md file
        """
        metadata_yaml = yaml.dump(skill.metadata.model_dump(), default_flow_style=False)

        body = f"""# Purpose
{skill.content.purpose}

# When to Use
{skill.content.when_to_use}

# How to Apply
{skill.content.how_to_apply}

# Example
{skill.content.example}
"""
        return f"---\n{metadata_yaml}---\n{body}"

    def skill_to_record(self, skill: Skill) -> SkillRecord:
        """Convert a Skill to a SkillRecord for database storage.

        Args:
            skill: The Skill to convert

        Returns:
            SkillRecord ready for database insertion
        """
        return SkillRecord(
            skill_id=skill.metadata.skill_id,
            name=skill.metadata.name,
            version=skill.metadata.version,
            description=skill.metadata.description,
            team_id=skill.metadata.team_id,
            tags=json.dumps(skill.metadata.tags),
            content_purpose=skill.content.purpose,
            content_when_to_use=skill.content.when_to_use,
            content_how_to_apply=skill.content.how_to_apply,
            content_example=skill.content.example,
            content_constraints=json.dumps(skill.content.constraints),
            content_prerequisites=json.dumps(skill.content.prerequisites),
        )

    def record_to_skill(self, record: SkillRecord) -> Skill:
        """Convert a SkillRecord to a Skill.

        Args:
            record: The SkillRecord to convert

        Returns:
            Skill object
        """
        return Skill(
            metadata=SkillMetadata(
                skill_id=record.skill_id,
                name=record.name,
                version=record.version,
                description=record.description,
                team_id=record.team_id,
                tags=self._parse_json_field(record.tags),
            ),
            content=SkillContent(
                purpose=record.content_purpose,
                when_to_use=record.content_when_to_use,
                how_to_apply=record.content_how_to_apply,
                example=record.content_example,
                constraints=self._parse_json_field(record.content_constraints),
                prerequisites=self._parse_json_field(record.content_prerequisites),
            ),
        )
