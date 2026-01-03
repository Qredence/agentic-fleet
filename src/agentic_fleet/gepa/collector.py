"""Trace collector for DSPy training examples with skill tracking."""

from __future__ import annotations

import ast
import json
from typing import Any

import dspy
from agent_framework import AgentRunEvent, AgentRunResponse

from agentic_fleet.config import TEAM_REGISTRY
from agentic_fleet.dspy_modules.signatures import TaskContext
from agentic_fleet.skills.repository import list_team_skills


def _parse_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(value)
            except Exception:
                continue
            if isinstance(parsed, dict):
                return parsed
    return None


def _extract_field(response: AgentRunResponse | None, key: str) -> Any:
    if response is None:
        return None

    if isinstance(response.value, dict) and key in response.value:
        return response.value[key]

    if isinstance(response.value, str):
        parsed = _parse_payload(response.value)
        if isinstance(parsed, dict) and key in parsed:
            return parsed[key]

    parsed_text = _parse_payload(response.text)
    if isinstance(parsed_text, dict) and key in parsed_text:
        return parsed_text[key]

    if response.additional_properties and key in response.additional_properties:
        return response.additional_properties[key]

    return None


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _coerce_str_list(value: Any) -> list[str]:
    """Convert value to string list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [_coerce_str(v) for v in value]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


class TraceCollector:
    """Extract training examples from workflow history with skill tracking."""

    def extract_examples(self, history: list[AgentRunEvent]) -> list[dspy.Example]:
        last_task: str | None = None
        last_plan: str | None = None
        last_result: str | None = None
        last_team_id: str | None = None
        last_mounted_skills: list[str] = []
        last_available_skills: list[str] = []
        examples: list[dspy.Example] = []

        for event in history:
            if not isinstance(event, AgentRunEvent):
                continue

            response = event.data
            if response is not None:
                mounted_skills = _extract_field(response, "mounted_skills")
                if mounted_skills is not None:
                    last_mounted_skills = _coerce_str_list(mounted_skills)

                available_skills = _extract_field(response, "available_skills")
                if available_skills is not None:
                    last_available_skills = _coerce_str_list(available_skills)
            if event.executor_id == "Router":
                task = _extract_field(response, "original_task")
                if task:
                    last_task = _coerce_str(task)
                team = _extract_field(response, "target_team")
                if team:
                    last_team_id = _coerce_str(team)
            elif event.executor_id == "Planner":
                plan = _extract_field(response, "plan")
                if plan is None:
                    plan = response.text if response else None
                last_plan = _coerce_str(plan)
            elif event.executor_id == "Worker":
                result = _extract_field(response, "result")
                if result is None:
                    result = response.text if response else None
                last_result = _coerce_str(result)
            elif event.executor_id == "Judge":
                approved = _extract_field(response, "is_approved")
                approved = _coerce_bool(approved)
                if approved is True and last_task and last_plan and last_result:
                    team_id = last_team_id or "default"
                    team_cfg = TEAM_REGISTRY.get(team_id, TEAM_REGISTRY["default"])
                    example = dspy.Example(
                        task=last_task,
                        context=TaskContext(
                            team_id=team_id,
                            constraints=[],
                            tools=list(team_cfg.get("tools", [])),
                            mounted_skills=last_mounted_skills,
                            available_skills=last_available_skills or list_team_skills(team_id),
                        ),
                        plan=last_plan,
                        result=last_result,
                    ).with_inputs("task", "context")
                    examples.append(example)

        return examples

    def extract_skill_usage(self, history: list[AgentRunEvent]) -> list[dict[str, Any]]:
        """Extract skill usage patterns for GEPA learning.

        Args:
            history: List of agent run events

        Returns:
            List of usage records with skill_id, task_type, success, team_id
        """
        usages: list[dict[str, Any]] = []
        current_run: dict[str, Any] = {
            "run_id": None,
            "team_id": None,
            "task": None,
            "mounted_skills": [],
            "required_skills": [],
            "was_successful": False,
        }

        for event in history:
            if not isinstance(event, AgentRunEvent):
                continue

            response = event.data
            if response is not None:
                mounted_skills = _extract_field(response, "mounted_skills")
                if mounted_skills is not None:
                    current_run["mounted_skills"] = _coerce_str_list(mounted_skills)

            if event.executor_id == "Router":
                task = _extract_field(response, "original_task")
                if task:
                    current_run["task"] = _coerce_str(task)
                team = _extract_field(response, "target_team")
                if team:
                    current_run["team_id"] = _coerce_str(team)
                required_skills = _extract_field(response, "required_skills")
                current_run["required_skills"] = _coerce_str_list(required_skills)

            elif event.executor_id == "Planner":
                required_skills = _extract_field(response, "required_skills")
                if required_skills is not None:
                    current_run["required_skills"] = _coerce_str_list(required_skills)

            elif event.executor_id == "Judge":
                approved = _extract_field(response, "is_approved")
                approved = _coerce_bool(approved)
                current_run["was_successful"] = approved is True

                # Create usage records for each mounted skill
                for skill_id in current_run["mounted_skills"]:
                    usages.append({
                        "skill_id": skill_id,
                        "task_type": self._classify_task(current_run["task"]),
                        "was_successful": current_run["was_successful"],
                        "team_id": current_run["team_id"] or "default",
                        "run_id": current_run["run_id"],
                    })

                # Reset for next run
                current_run = {
                    "run_id": None,
                    "team_id": None,
                    "task": None,
                    "mounted_skills": [],
                    "required_skills": [],
                    "was_successful": False,
                }

        return usages

    @staticmethod
    def _classify_task(task: str | None) -> str:
        """Classify task type for skill pattern analysis."""
        if not task:
            return "general"

        task_lower = task.lower()

        if any(kw in task_lower for kw in ["search", "research", "find", "look up"]):
            return "research"
        if any(kw in task_lower for kw in ["code", "implement", "fix", "debug", "write"]):
            return "coding"
        if any(kw in task_lower for kw in ["write", "compose", "draft", "create"]):
            return "writing"
        if any(kw in task_lower for kw in ["analyze", "review", "evaluate", "assess"]):
            return "analysis"
        return "general"
