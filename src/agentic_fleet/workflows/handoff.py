"""
HandoffManager for intelligent agent-to-agent handoffs.

Manages the complete handoff lifecycle:
- Evaluating when handoffs are needed
- Creating structured handoff packages
- Tracking handoff history and statistics
- Assessing handoff quality
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import dspy

if TYPE_CHECKING:
    from ..dspy_modules.reasoner import DSPyReasoner

from ..dspy_modules.handoff_signatures import (
    HandoffDecision,
    HandoffProtocol,
    HandoffQualityAssessment,
)

logger = logging.getLogger(__name__)


@dataclass
class HandoffContext:
    """Rich context passed between agents during handoff.

    Contains all necessary information for the receiving agent to
    continue work seamlessly, including completed work, artifacts,
    objectives, and quality criteria.
    """

    from_agent: str
    to_agent: str
    task: str
    work_completed: str
    artifacts: dict[str, Any]
    remaining_objectives: list[str]
    success_criteria: list[str]
    tool_requirements: list[str]
    estimated_effort: str  # simple|moderate|complex
    quality_checklist: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    handoff_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "task": self.task,
            "work_completed": self.work_completed,
            "artifacts": self.artifacts,
            "remaining_objectives": self.remaining_objectives,
            "success_criteria": self.success_criteria,
            "tool_requirements": self.tool_requirements,
            "estimated_effort": self.estimated_effort,
            "quality_checklist": self.quality_checklist,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "handoff_reason": self.handoff_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandoffContext:
        """Create from dictionary."""
        data_copy = data.copy()
        if "timestamp" in data_copy:
            data_copy["timestamp"] = datetime.fromisoformat(data_copy["timestamp"])
        return cls(**data_copy)


class HandoffManager:
    """Manages agent-to-agent handoffs with DSPy intelligence.

    Provides methods to:
    - Evaluate if handoff is needed
    - Create structured handoff packages
    - Track handoff history
    - Assess handoff quality
    - Generate handoff statistics
    """

    def __init__(
        self,
        dspy_supervisor: DSPyReasoner,
        get_compiled_supervisor: Callable[[], DSPyReasoner] | None = None,
    ):
        """Initialize HandoffManager.

        Args:
            dspy_supervisor: DSPy reasoner module for intelligent decisions
            get_compiled_supervisor: Optional provider that returns the compiled reasoner.
                When provided, handoff chains are invoked on the compiled reasoner;
                otherwise local ChainOfThought fallbacks are used.
        """
        self.supervisor = dspy_supervisor
        self._get_compiled_supervisor = get_compiled_supervisor

        # Only create raw ChainOfThought fallbacks if a compiled supervisor provider is NOT given.
        self.handoff_decision_module = (
            None if get_compiled_supervisor is not None else dspy.ChainOfThought(HandoffDecision)  # type: ignore[arg-type]
        )
        self.handoff_protocol_module = (
            None if get_compiled_supervisor is not None else dspy.ChainOfThought(HandoffProtocol)  # type: ignore[arg-type]
        )
        self.handoff_quality_module = (
            None
            if get_compiled_supervisor is not None
            else dspy.ChainOfThought(HandoffQualityAssessment)  # type: ignore[arg-type]
        )
        self.handoff_history: list[HandoffContext] = []

    def _sup(self) -> DSPyReasoner:
        """Return preferred reasoner (compiled if provider is available).

        Attempts to retrieve the compiled DSPy reasoner from the provider.
        Falls back to the base supervisor if the provider fails or is unavailable.

        Returns:
            The compiled DSPyReasoner if available, otherwise the base supervisor.
        """
        if self._get_compiled_supervisor is not None:
            try:
                sup = self._get_compiled_supervisor()
                if sup is not None:
                    return sup
            except Exception as e:
                # Fall back to base supervisor on any error
                logger.warning(f"Error getting compiled supervisor, falling back to base: {e}")
        return self.supervisor

    async def evaluate_handoff(
        self,
        current_agent: str,
        work_completed: str,
        remaining_work: str,
        available_agents: dict[str, str],
        agent_states: dict[str, str] | None = None,
    ) -> str | None:
        """
        Determine whether the task should be handed off to another agent using the DSPy supervisor.

        Parameters:
            current_agent (str): Name of the agent currently handling the task.
            work_completed (str): Brief summary of work already performed.
            remaining_work (str): Description of remaining tasks or objectives.
            available_agents (dict[str, str]): Mapping of agent name to capability/description.
            agent_states (dict[str, str] | None): Optional mapping of agent name to
                current state; if omitted, agents are treated as "available".

        Returns:
            str | None: Name of the agent to receive the handoff if a handoff is recommended, `None` otherwise.
        """
        if not available_agents:
            logger.debug("No agents available for handoff")
            return None

        # Prepare agent states
        if agent_states is None:
            agent_states = dict.fromkeys(available_agents, "available")

        # Format agents for DSPy
        agents_desc = "\n".join(
            [
                f"{name}: {desc} (state: {agent_states.get(name, 'unknown')})"
                for name, desc in available_agents.items()
            ]
        )

        states_desc = "\n".join([f"{name}: {state}" for name, state in agent_states.items()])

        try:
            # Get handoff decision from DSPy (prefer compiled supervisor chains)
            sup = self._sup()
            if hasattr(sup, "handoff_decision"):
                decision = sup.handoff_decision(
                    current_agent=current_agent,
                    work_completed=work_completed,
                    remaining_work=remaining_work,
                    available_agents=agents_desc,
                    agent_states=states_desc,
                )
            else:
                module = self.handoff_decision_module or dspy.ChainOfThought(
                    HandoffDecision  # type: ignore[arg-type]
                )
                decision = module(
                    current_agent=current_agent,
                    work_completed=work_completed,
                    remaining_work=remaining_work,
                    available_agents=agents_desc,
                    agent_states=states_desc,
                )

            # Parse decision
            should_handoff_str = str(getattr(decision, "should_handoff", "")).lower().strip()
            should_handoff = should_handoff_str in ("yes", "true", "1", "y")

            if should_handoff and getattr(decision, "next_agent", None):
                next_agent = str(getattr(decision, "next_agent", "")).strip()
                logger.info(f"Handoff recommended: {current_agent} → {next_agent}")
                logger.info(f"Reason: {getattr(decision, 'handoff_reason', '')}")
                return next_agent

            logger.debug(f"No handoff needed, {current_agent} should continue")
            return None

        except Exception as e:
            logger.error(f"Error evaluating handoff: {e}")
            return None

    async def create_handoff_package(
        self,
        from_agent: str,
        to_agent: str,
        work_completed: str,
        artifacts: dict[str, Any],
        remaining_objectives: list[str],
        task: str | None = None,
        handoff_reason: str = "",
    ) -> HandoffContext:
        """
        Builds a HandoffContext that packages work, artifacts, objectives, and a
        DSPy-generated protocol for transferring responsibility between agents.

        This method derives measurable success criteria from the remaining objectives,
        identifies tools the receiving agent may need, and requests a structured handoff
        protocol (including an estimated effort and a quality checklist) from the
        supervisor/ChainOfThought when available. The resulting HandoffContext is appended
        to the manager's history before being returned. On error, a minimal fallback
        HandoffContext with conservative defaults is returned.

        Parameters:
            from_agent (str): Agent initiating the handoff.
            to_agent (str): Agent intended to receive and continue the work.
            work_completed (str): Human-readable summary of what the initiating agent
                completed.
            artifacts (dict[str, Any]): Collected outputs, files, or data produced so far
                (serializable).
            remaining_objectives (list[str]): List of tasks or objectives the receiving
                agent should accomplish next.
            task (str | None): Optional original or overarching task description; if
                omitted, work_completed is used.
            handoff_reason (str): Short description of why the handoff is occurring.

        Returns:
            HandoffContext: A fully populated handoff package including derived success
                criteria, required tools, estimated effort, quality checklist (from the
                protocol when available), metadata containing the protocol package, and
                the original fields provided.
        """
        # Derive success criteria from objectives
        success_criteria = self._derive_success_criteria(remaining_objectives)

        # Identify required tools
        tool_requirements = self._identify_required_tools(to_agent)

        try:
            # Prepare common protocol parameters
            protocol_params = {
                "from_agent": from_agent,
                "to_agent": to_agent,
                "work_completed": work_completed,
                "artifacts": json.dumps(artifacts, indent=2),
                "remaining_objectives": "\n".join(f"- {obj}" for obj in remaining_objectives),
                "success_criteria": "\n".join(f"- {crit}" for crit in success_criteria),
                "tool_requirements": ", ".join(tool_requirements) if tool_requirements else "None",
            }

            # Get structured handoff protocol from DSPy (prefer compiled supervisor chains)
            sup = self._sup()
            if hasattr(sup, "handoff_protocol"):
                protocol = sup.handoff_protocol(**protocol_params)
            else:
                module = self.handoff_protocol_module or dspy.ChainOfThought(
                    HandoffProtocol  # type: ignore[arg-type]
                )
                protocol = module(**protocol_params)

            # Parse quality checklist
            checklist = self._parse_checklist(str(getattr(protocol, "quality_checklist", "")))

            # Create handoff context
            handoff_context = HandoffContext(
                from_agent=from_agent,
                to_agent=to_agent,
                task=task or work_completed,
                work_completed=work_completed,
                artifacts=artifacts,
                remaining_objectives=remaining_objectives,
                success_criteria=success_criteria,
                tool_requirements=tool_requirements,
                estimated_effort=str(getattr(protocol, "estimated_effort", "moderate")).lower(),
                quality_checklist=checklist,
                metadata={"protocol_package": getattr(protocol, "handoff_package", "")},
                handoff_reason=handoff_reason,
            )

            # Store in history
            # Append the full HandoffContext object to handoff_history.
            # This captures all relevant handoff data (agents, objectives, artifacts, quality checklist, etc.)
            # for later analysis of handoff quality, pattern tracking, and auditability.
            self.handoff_history.append(handoff_context)
            logger.info(f"Handoff package created: {from_agent} → {to_agent}")
            logger.debug(f"Estimated effort: {handoff_context.estimated_effort}")

            return handoff_context

        except Exception as e:
            logger.error(f"Error creating handoff package: {e}")
            # Create minimal handoff context as fallback
            return HandoffContext(
                from_agent=from_agent,
                to_agent=to_agent,
                task=task or work_completed,
                work_completed=work_completed,
                artifacts=artifacts,
                remaining_objectives=remaining_objectives,
                success_criteria=success_criteria,
                tool_requirements=tool_requirements,
                estimated_effort="moderate",
                quality_checklist=["Verify handoff context is complete"],
                handoff_reason=handoff_reason,
            )

    async def assess_handoff_quality(
        self,
        handoff_context: HandoffContext,
        work_after_handoff: str,
    ) -> dict[str, Any]:
        """
        Evaluate the quality of a completed handoff between agents.

        Parameters:
            handoff_context (HandoffContext): The structured context describing the handoff that occurred.
            work_after_handoff (str): Description of the work performed by the receiving agent after the handoff.

        Returns:
            dict[str, Any]: Assessment result containing:
                - quality_score (float): Parsed numeric quality score (higher is better;
                    defaults to 5.0 on parse failure).
                - context_complete (bool): `True` if the assessment indicates the handoff
                    context was complete, `False` otherwise.
                - success_factors (Any): Key factors that contributed to successful handoff
                    (string or structured data).
                - improvements (Any): Suggested improvement areas for future handoffs
                    (string or structured data).
        """
        try:
            sup = self._sup()
            if hasattr(sup, "handoff_quality_assessor"):
                assessment = sup.handoff_quality_assessor(
                    handoff_context=json.dumps(handoff_context.to_dict(), indent=2),
                    from_agent=handoff_context.from_agent,
                    to_agent=handoff_context.to_agent,
                    work_completed=work_after_handoff,
                )
            else:
                module = self.handoff_quality_module or dspy.ChainOfThought(
                    HandoffQualityAssessment  # type: ignore[arg-type]
                )
                assessment = module(
                    handoff_context=json.dumps(handoff_context.to_dict(), indent=2),
                    from_agent=handoff_context.from_agent,
                    to_agent=handoff_context.to_agent,
                    work_completed=work_after_handoff,
                )

            return {
                "quality_score": self._parse_score(
                    getattr(assessment, "handoff_quality_score", "5.0")
                ),
                "context_complete": str(getattr(assessment, "context_completeness", "")).lower()
                in ("yes", "true", "1"),
                "success_factors": getattr(assessment, "success_factors", "Unknown"),
                "improvements": getattr(assessment, "improvement_areas", "Unable to assess"),
            }

        except Exception as e:
            logger.error(f"Error assessing handoff quality: {e}")
            return {
                "quality_score": 5.0,
                "context_complete": True,
                "success_factors": "Unknown",
                "improvements": "Unable to assess",
            }

    def get_handoff_summary(self) -> dict[str, Any]:
        """Get statistics on handoffs.

        Returns:
            Dictionary with handoff statistics
        """
        if not self.handoff_history:
            return {
                "total_handoffs": 0,
                "handoff_pairs": {},
                "avg_handoffs_per_task": 0.0,
                "most_common_handoffs": [],
            }

        return {
            "total_handoffs": len(self.handoff_history),
            "handoff_pairs": self._count_handoff_pairs(),
            "avg_handoffs_per_task": self._calculate_avg_handoffs(),
            "most_common_handoffs": self._get_common_handoffs(top_n=5),
            "effort_distribution": self._get_effort_distribution(),
        }

    def _derive_success_criteria(self, objectives: list[str]) -> list[str]:
        """Derive success criteria from objectives.

        Converts high-level objectives into measurable success criteria
        by analyzing the objective type (analyze, create, find, etc.).

        Args:
            objectives: List of remaining objectives for the task.

        Returns:
            List of measurable success criteria strings.
        """
        if not objectives:
            return ["Task completed successfully"]

        criteria = []
        for obj in objectives:
            # Convert objective to measurable criterion
            if "analyze" in obj.lower():
                criteria.append(f"Analysis complete for: {obj}")
            elif "create" in obj.lower() or "generate" in obj.lower():
                criteria.append(f"Generated: {obj}")
            elif "find" in obj.lower() or "search" in obj.lower():
                criteria.append(f"Found and validated: {obj}")
            else:
                criteria.append(f"Completed: {obj}")

        return criteria

    def _identify_required_tools(self, agent_name: str) -> list[str]:
        """Identify tools required by the receiving agent.

        Queries the tool registry to find tools assigned to the specified agent.

        Args:
            agent_name: Name of the agent receiving the handoff.

        Returns:
            List of tool names available to the agent, empty if no registry.
        """
        # Use reasoner's tool registry if available
        if hasattr(self.supervisor, "tool_registry") and self.supervisor.tool_registry:
            agent_tools = self.supervisor.tool_registry.get_agent_tools(agent_name)
            return [tool.name for tool in agent_tools]
        return []

    def _parse_checklist(self, checklist_str: str) -> list[str]:
        """Parse quality checklist from DSPy output.

        Extracts individual checklist items from DSPy-generated text,
        removing common bullet point prefixes.

        Args:
            checklist_str: Raw checklist string from DSPy output.

        Returns:
            List of cleaned checklist items.
        """
        if not checklist_str:
            return ["Verify handoff context"]

        # Split by newlines and clean up
        items = []
        for line in checklist_str.split("\n"):
            line = line.strip()
            # Remove common prefixes
            for prefix in ["- ", "* ", "• ", "[] ", "[ ] "]:
                if line.startswith(prefix):
                    line = line[len(prefix) :].strip()
            if line:
                items.append(line)

        return items if items else ["Verify handoff context"]

    def _parse_score(self, score_str: str) -> float:
        """Parse quality score from DSPy output.

        Handles various score formats including "8/10" and "8.5".

        Args:
            score_str: Raw score string from DSPy output.

        Returns:
            Parsed float score, defaults to 5.0 on parsing failure.
        """
        try:
            # Extract numeric value from strings like "8/10" or "8.5"
            if "/" in score_str:
                return float(score_str.split("/")[0])
            return float(score_str)
        except (ValueError, AttributeError):
            return 5.0  # Default middle score

    def _count_handoff_pairs(self) -> dict[str, int]:
        """Count occurrences of each handoff pair.

        Analyzes handoff history to identify common agent-to-agent patterns.

        Returns:
            Dictionary mapping "FromAgent → ToAgent" strings to occurrence counts.
        """
        pairs: dict[str, int] = {}
        for handoff in self.handoff_history:
            pair = f"{handoff.from_agent} → {handoff.to_agent}"
            pairs[pair] = pairs.get(pair, 0) + 1
        return pairs

    def _calculate_avg_handoffs(self) -> float:
        """Calculate average handoffs per task.

        Note: This is a simplified implementation that returns total handoffs.
        A full implementation would track unique tasks and compute true averages.

        Returns:
            Total number of handoffs (simplified metric).
        """
        if not self.handoff_history:
            return 0.0

        # Group by task (approximate - use timestamp proximity)
        # For now, return total / estimated unique tasks
        # This is simplified - real implementation would track tasks
        return float(len(self.handoff_history))

    def _get_common_handoffs(self, top_n: int = 5) -> list[tuple]:
        """Get most common handoff patterns.

        Args:
            top_n: Maximum number of patterns to return.

        Returns:
            List of (pair_string, count) tuples sorted by frequency descending.
        """
        pairs = self._count_handoff_pairs()
        sorted_pairs = sorted(pairs.items(), key=lambda x: x[1], reverse=True)
        return sorted_pairs[:top_n]

    def _get_effort_distribution(self) -> dict[str, int]:
        """Get distribution of estimated effort across handoffs.

        Aggregates estimated effort levels (simple, moderate, complex)
        from handoff history.

        Returns:
            Dictionary mapping effort level to count.
        """
        distribution = {"simple": 0, "moderate": 0, "complex": 0}
        for handoff in self.handoff_history:
            effort = handoff.estimated_effort.lower()
            if effort in distribution:
                distribution[effort] += 1
        return distribution

    def clear_history(self) -> None:
        """Clear handoff history.

        Removes all stored handoff records. Useful for testing
        or when starting a new session.
        """
        self.handoff_history.clear()
        logger.info("Handoff history cleared")

    def export_history(self, filepath: str):
        """Export handoff history to JSON file.

        Args:
            filepath: Path to output file
        """
        try:
            data = [handoff.to_dict() for handoff in self.handoff_history]
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Handoff history exported to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting handoff history: {e}")
