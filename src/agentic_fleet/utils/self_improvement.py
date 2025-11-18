"""
Self-improvement utilities for learning from execution history.

This module analyzes execution history and automatically generates
new DSPy training examples from high-quality executions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .cosmos import get_default_user_id, mirror_dspy_examples, save_agent_memory_item
from .history_manager import HistoryManager

logger = logging.getLogger(__name__)


class SelfImprovementEngine:
    """
    Engine for self-improvement based on execution history.

    Analyzes execution history, identifies high-quality executions,
    and generates new training examples for DSPy optimization.
    """

    def __init__(
        self,
        min_quality_score: float = 8.0,
        max_examples_to_add: int = 20,
        history_lookback: int = 100,
        user_id: str | None = None,
    ):
        """
        Initialize self-improvement engine.

        Args:
            min_quality_score: Minimum quality score to consider (0-10)
            max_examples_to_add: Maximum new examples to generate per analysis
            history_lookback: Number of recent executions to analyze
        """
        self.min_quality_score = min_quality_score
        self.max_examples_to_add = max_examples_to_add
        self.history_lookback = history_lookback
        self.history_manager = HistoryManager()
        self.user_id = user_id or get_default_user_id()

    def analyze_and_improve(
        self, examples_file: str = "data/supervisor_examples.json"
    ) -> dict[str, Any]:
        """
        Analyze execution history and generate new training examples.

        Args:
            examples_file: Path to training examples file

        Returns:
            Dictionary with improvement statistics
        """
        logger.info("Starting self-improvement analysis...")

        # Load execution history
        executions = self.history_manager.load_history(limit=self.history_lookback)

        if not executions:
            logger.warning("No execution history found for self-improvement")
            return {
                "new_examples_added": 0,
                "high_quality_executions": 0,
                "total_analyzed": 0,
            }

        # Filter high-quality executions
        high_quality = self._filter_high_quality_executions(executions)

        logger.info(
            f"Found {len(high_quality)} high-quality executions (score >= {self.min_quality_score})"
        )

        if not high_quality:
            return {
                "new_examples_added": 0,
                "high_quality_executions": 0,
                "total_analyzed": len(executions),
            }

        # Convert to training examples
        new_examples = self._convert_to_training_examples(high_quality)

        # Load existing examples
        existing_examples = self._load_existing_examples(examples_file)

        # Deduplicate and add new examples
        added_examples = self._add_new_examples(existing_examples, new_examples, examples_file)

        logger.info(f"Added {len(added_examples)} new training examples")

        return {
            "new_examples_added": len(added_examples),
            "high_quality_executions": len(high_quality),
            "total_analyzed": len(executions),
            "min_quality_score": self.min_quality_score,
            "examples_file": examples_file,
        }

    def _filter_high_quality_executions(
        self, executions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Filter executions with quality score >= threshold."""
        high_quality = []

        for execution in executions:
            quality = execution.get("quality", {})
            score = quality.get("score", 0)

            if score >= self.min_quality_score:
                high_quality.append(execution)

        return high_quality

    def _detect_edge_cases_in_execution(self, execution: dict[str, Any]) -> list[str]:
        """
        Detect edge cases in an execution that could inform training examples.

        Returns list of edge case descriptions.
        """
        edge_cases = []
        task = execution.get("task", "").lower()
        routing = execution.get("routing", {})
        quality = execution.get("quality", {})

        # Detect ambiguous tasks
        ambiguous_keywords = ["maybe", "possibly", "could", "might", "perhaps", "either", "or"]
        if any(kw in task for kw in ambiguous_keywords):
            edge_cases.append("ambiguous_task")

        # Detect time-sensitive queries
        time_keywords = ["latest", "current", "recent", "today", "now", "2025", "2026", "future"]
        if any(kw in task for kw in time_keywords):
            edge_cases.append("time_sensitive")

        # Detect mode edge cases
        mode = routing.get("mode", "")
        assigned_to = routing.get("assigned_to", [])
        if mode == "parallel" and len(assigned_to) == 1:
            edge_cases.append("parallel_single_agent")
        elif mode == "sequential" and len(assigned_to) == 1:
            edge_cases.append("sequential_single_agent")

        # Detect tool assignment issues
        tool_requirements = routing.get("tool_requirements", [])
        if not tool_requirements and any(kw in task for kw in time_keywords):
            edge_cases.append("missing_web_search_tool")

        # Detect low quality with specific patterns
        score = quality.get("score", 0)
        if score < self.min_quality_score and "improvements" in quality:
            improvements = quality.get("improvements", "")
            if "agent" in improvements.lower() or "routing" in improvements.lower():
                edge_cases.append("routing_failure")

        return edge_cases

    def _generate_clarifying_example_from_edge_case(
        self, execution: dict[str, Any], edge_case: str
    ) -> dict[str, Any] | None:
        """
        Generate a clarifying example from an edge case execution.

        Args:
            execution: Execution dictionary
            edge_case: Type of edge case detected

        Returns:
            Training example dictionary with clarifying context
        """
        example = self.execution_to_example(execution)
        if not example:
            return None

        # Add edge case context to help DSPy learn
        context_prefix = f"Edge case: {edge_case.replace('_', ' ').title()}"
        if example.get("context"):
            example["context"] = f"{context_prefix} - {example['context']}"
        else:
            example["context"] = context_prefix

        # Add clarifying guidance based on edge case type
        if edge_case == "ambiguous_task":
            example["context"] += (
                " - Ambiguous tasks should default to Researcher for clarification"
            )
        elif edge_case == "time_sensitive":
            example["context"] += " - Time-sensitive queries require TavilySearchTool"
        elif edge_case == "parallel_single_agent":
            example["context"] += " - Parallel mode typically requires multiple agents"
        elif edge_case == "sequential_single_agent":
            example["context"] += (
                " - Sequential mode typically requires multiple agents with dependencies"
            )
        elif edge_case == "missing_web_search_tool":
            example["context"] += " - Time-sensitive queries need web search tool"
        elif edge_case == "routing_failure":
            example["context"] += " - Learn from routing failure pattern"

        return example

    def _convert_to_training_examples(
        self, executions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Convert high-quality executions to DSPy training examples.
        Also captures edge cases from failed routings to generate clarifying examples.

        Args:
            executions: List of high-quality execution dictionaries

        Returns:
            List of training example dictionaries
        """
        # Sort executions by quality score first
        sorted_executions = sorted(
            executions, key=lambda x: x.get("quality", {}).get("score", 0), reverse=True
        )

        examples = []
        edge_case_examples = []

        for execution in sorted_executions:
            try:
                # Convert successful execution to example
                example = self.execution_to_example(execution)
                if example:
                    examples.append(example)
                    self._record_memory_from_execution(execution, example)

                # Also check for edge cases even in successful executions
                edge_cases = self._detect_edge_cases_in_execution(execution)
                for edge_case in edge_cases:
                    clarifying_example = self._generate_clarifying_example_from_edge_case(
                        execution, edge_case
                    )
                    if clarifying_example:
                        edge_case_examples.append(clarifying_example)
                        self._record_memory_from_execution(
                            execution,
                            clarifying_example,
                            memory_type="edge_case_example",
                        )
            except Exception as e:
                logger.warning(f"Failed to convert execution to example: {e}")
                continue

        # Also capture edge cases from failed routings (low quality executions)
        all_executions = self.history_manager.load_history(limit=self.history_lookback)
        failed_executions = [
            ex
            for ex in all_executions
            if ex.get("quality", {}).get("score", 0) < self.min_quality_score
        ]

        for execution in failed_executions[:10]:  # Limit to avoid too many examples
            try:
                edge_cases = self._detect_edge_cases_in_execution(execution)
                for edge_case in edge_cases:
                    clarifying_example = self._generate_clarifying_example_from_edge_case(
                        execution, edge_case
                    )
                    if clarifying_example:
                        edge_case_examples.append(clarifying_example)
                        self._record_memory_from_execution(
                            execution,
                            clarifying_example,
                            memory_type="edge_case_example",
                        )
            except Exception as e:
                logger.debug(f"Failed to process edge case from failed execution: {e}")
                continue

        # Combine examples, prioritizing high-quality ones
        # Add edge case examples (up to 30% of max)
        max_edge_cases = max(1, int(self.max_examples_to_add * 0.3))
        combined_examples = examples + edge_case_examples[:max_edge_cases]

        # Limit total number of examples
        if len(combined_examples) > self.max_examples_to_add:
            combined_examples = combined_examples[: self.max_examples_to_add]

        if edge_case_examples:
            logger.info(f"Captured {len(edge_case_examples[:max_edge_cases])} edge case examples")

        return combined_examples

    def execution_to_example(self, execution: dict[str, Any]) -> dict[str, Any] | None:
        """
        Convert a single execution to a training example.

        Args:
            execution: Execution dictionary from history

        Returns:
            Training example dictionary or None if conversion fails
        """
        # Extract required fields
        task = execution.get("task")
        routing = execution.get("routing", {})

        if not task or not routing:
            return None

        assigned_to = routing.get("assigned_to", [])
        mode = routing.get("mode", "delegated")
        tool_requirements = routing.get("tool_requirements", [])

        # Build team description (simplified from actual agents)
        team_lines = []
        if "Researcher" in assigned_to or "researcher" in task.lower():
            team_lines.append("Researcher: Web research specialist")
        if "Analyst" in assigned_to or "analysis" in task.lower():
            team_lines.append("Analyst: Data analysis expert")
        if "Writer" in assigned_to or "write" in task.lower() or "create" in task.lower():
            team_lines.append("Writer: Content creation")
        if "Reviewer" in assigned_to or "review" in task.lower():
            team_lines.append("Reviewer: Quality assurance")

        if not team_lines:
            team_lines = ["Writer: Content creation"]  # Default

        team = "\n".join(team_lines)

        # Build available tools description
        available_tools = self._build_tools_description(assigned_to, tool_requirements)

        # Create training example
        example = {
            "task": task,
            "team": team,
            "available_tools": available_tools,
            "context": f"Self-improvement: Quality score {execution.get('quality', {}).get('score', 0):.1f}/10",
            "assigned_to": ",".join(assigned_to),
            "mode": mode,
            "tool_requirements": tool_requirements,
        }

        return example

    def _build_tools_description(self, agents: list[str], tool_requirements: list[str]) -> str:
        """Build tools description for training example."""
        tools_desc = []

        tool_requirements_text = "|".join(tool_requirements).lower()

        if (
            "Researcher" in agents
            or "TavilySearchTool" in tool_requirements
            or "tavily" in tool_requirements_text
        ):
            tools_desc.append(
                "- TavilySearchTool/TavilyMCPTool (available to Researcher): Search the web for real-time "
                "information using Tavily. Provides accurate, up-to-date results with source "
                "citations. [Capabilities: web_search, real_time, citations]"
            )

        if "Analyst" in agents or "HostedCodeInterpreterTool" in tool_requirements:
            tools_desc.append(
                "- HostedCodeInterpreterTool (available to Analyst): Execute Python snippets "
                "in a managed sandbox. [Capabilities: code_execution]"
            )

        return "\n".join(tools_desc) if tools_desc else "No tools available"

    def _load_existing_examples(self, examples_file: str) -> list[dict[str, Any]]:
        """Load existing training examples."""
        examples_path = Path(examples_file)

        if not examples_path.exists():
            logger.warning(f"Training examples file not found: {examples_file}")
            return []

        try:
            with open(examples_path) as f:
                raw = json.load(f)
                # Ensure we return a list[dict[str, Any]]; discard malformed content
                if isinstance(raw, list) and all(isinstance(item, dict) for item in raw):
                    return raw  # type: ignore[return-value]
                logger.warning(
                    "Training examples file did not contain a list of objects; ignoring content"
                )
                return []
        except Exception as e:
            logger.error(f"Failed to load existing examples: {e}")
            return []

    def _add_new_examples(
        self,
        existing: list[dict[str, Any]],
        new: list[dict[str, Any]],
        examples_file: str,
    ) -> list[dict[str, Any]]:
        """
        Add new examples to existing set, avoiding duplicates.

        Args:
            existing: Existing training examples
            new: New examples to add
            examples_file: Path to examples file

        Returns:
            List of added examples
        """
        # Create set of existing task fingerprints for deduplication
        existing_fingerprints = {self._create_fingerprint(ex) for ex in existing}

        # Filter out duplicates
        unique_new = []
        for example in new:
            fingerprint = self._create_fingerprint(example)
            if fingerprint not in existing_fingerprints:
                unique_new.append(example)
                existing_fingerprints.add(fingerprint)

        if not unique_new:
            logger.info("No new unique examples to add")
            return []

        # Add to existing
        updated = existing + unique_new

        # Save updated examples
        try:
            examples_path = Path(examples_file)
            examples_path.parent.mkdir(parents=True, exist_ok=True)

            with open(examples_path, "w") as f:
                json.dump(updated, f, indent=2)

            logger.info(
                f"Saved {len(updated)} total examples to {examples_file} ({len(unique_new)} new)"
            )

            if unique_new:
                mirror_dspy_examples(unique_new, user_id=self.user_id)

            return unique_new

        except Exception as e:
            logger.error(f"Failed to save updated examples: {e}")
            return []

    def _create_fingerprint(self, example: dict[str, Any]) -> str:
        """
        Create unique fingerprint for deduplication.

        Uses task + assigned_to + mode to identify duplicates.
        """
        task = example.get("task", "").lower().strip()
        assigned_to = example.get("assigned_to", "")
        mode = example.get("mode", "")

        return f"{task}|{assigned_to}|{mode}"

    def _record_memory_from_execution(
        self,
        execution: dict[str, Any],
        example: dict[str, Any],
        *,
        memory_type: str = "execution_insight",
    ) -> None:
        """Persist distilled insights from executions into Cosmos agent memory."""

        if not self.user_id:
            return

        routing = execution.get("routing", {}) or {}
        assigned = routing.get("assigned_to") or []
        if isinstance(assigned, str):
            agents = [agent.strip() for agent in assigned.split(",") if agent.strip()]
        else:
            agents = list(assigned)

        fingerprint = self._create_fingerprint(example)
        summary = execution.get("result") or example.get("context") or ""

        item = {
            "memoryId": f"{execution.get('workflowId', 'unknown')}|{fingerprint}",
            "userId": self.user_id,
            "agentId": agents[0] if agents else "unknown",
            "memoryType": memory_type,
            "task": execution.get("task"),
            "content": summary,
            "workflowId": execution.get("workflowId"),
            "source": "self_improvement",
            "metadata": {
                "agents": agents,
                "mode": routing.get("mode"),
                "toolRequirements": routing.get("tool_requirements", []),
                "qualityScore": execution.get("quality", {}).get("score"),
                "exampleContext": example.get("context"),
            },
        }

        save_agent_memory_item(item, user_id=self.user_id)

    def get_improvement_stats(self) -> dict[str, Any]:
        """
        Get statistics about potential for self-improvement.

        Returns:
            Dictionary with statistics
        """
        executions = self.history_manager.load_history()

        if not executions:
            return {"potential_examples": 0, "total_executions": 0}

        high_quality = self._filter_high_quality_executions(executions)
        quality_scores = [
            ex.get("quality", {}).get("score", 0) for ex in executions if "quality" in ex
        ]

        return {
            "total_executions": len(executions),
            "high_quality_executions": len(high_quality),
            "potential_new_examples": len(high_quality),
            "min_quality_threshold": self.min_quality_score,
            "average_quality_score": (
                sum(quality_scores) / len(quality_scores) if quality_scores else 0
            ),
            "quality_score_distribution": {
                "excellent (9-10)": len([s for s in quality_scores if s >= 9]),
                "good (8-9)": len([s for s in quality_scores if 8 <= s < 9]),
                "acceptable (7-8)": len([s for s in quality_scores if 7 <= s < 8]),
                "needs_improvement (<7)": len([s for s in quality_scores if s < 7]),
            },
        }

    def auto_improve(
        self,
        examples_file: str = "data/supervisor_examples.json",
        force_recompile: bool = True,
    ) -> tuple[int, str]:
        """
        Automatically improve by adding examples from history and recompiling.

        Args:
            examples_file: Path to training examples file
            force_recompile: Whether to force DSPy recompilation

        Returns:
            Tuple of (number of examples added, status message)
        """
        stats = self.analyze_and_improve(examples_file)

        added = stats["new_examples_added"]

        if added > 0:
            status = (
                f"✓ Self-improvement: Added {added} new high-quality examples "
                f"from execution history. "
            )

            if force_recompile:
                # Clear cache to force recompilation with new examples
                try:
                    from .compiler import clear_cache

                    clear_cache()
                    status += "Cache cleared for recompilation."
                except Exception as e:
                    logger.warning(f"Failed to clear cache: {e}")

            return added, status
        else:
            return 0, "No new high-quality examples found for self-improvement."
