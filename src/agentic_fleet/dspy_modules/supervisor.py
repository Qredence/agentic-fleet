"""
DSPy Supervisor Module for intelligent workflow orchestration.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import dspy

from ..utils.models import ExecutionMode, RoutingDecision
from .handoff_signatures import HandoffDecision, HandoffProtocol, HandoffQualityAssessment
from .signatures import (
    ProgressEvaluation,
    QualityAssessment,
    TaskAnalysis,
    TaskRouting,
    ToolAwareTaskAnalysis,
)
from .workflow_signatures import EnhancedTaskRouting, JudgeEvaluation, WorkflowHandoffDecision

logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from ..utils.tool_registry import ToolRegistry  # type: ignore


class DSPySupervisor(dspy.Module):
    """
    Supervisor enhanced with DSPy for intelligent workflow orchestration.
    """

    def __init__(self, use_enhanced_signatures: bool = True):
        """Initialize DSPySupervisor.

        Args:
            use_enhanced_signatures: If True, use EnhancedTaskRouting and JudgeEvaluation
                from workflow_signatures.py for better agent-framework integration.
                If False, use the simpler TaskRouting and QualityAssessment signatures.
        """
        super().__init__()
        self.task_analyzer = dspy.ChainOfThought(TaskAnalysis)
        self.tool_aware_analyzer = dspy.ChainOfThought(ToolAwareTaskAnalysis)
        # Use enhanced routing signature if enabled (better workflow integration)
        if use_enhanced_signatures:
            self.task_router = dspy.ChainOfThought(EnhancedTaskRouting)
            self.enhanced_routing_enabled = True
        else:
            self.task_router = dspy.ChainOfThought(TaskRouting)
            self.enhanced_routing_enabled = False
        self.progress_evaluator = dspy.ChainOfThought(ProgressEvaluation)
        # Use enhanced judge signature if enabled
        if use_enhanced_signatures:
            self.judge_evaluator = dspy.ChainOfThought(JudgeEvaluation)
            self.enhanced_judge_enabled = True
        else:
            self.quality_assessor = dspy.ChainOfThought(QualityAssessment)
            self.enhanced_judge_enabled = False
        self.routing_history: list[RoutingDecision] = []
        self.execution_context = []
        self.tool_registry: ToolRegistry | None = None
        self.enable_tool_usage: bool = True
        # Handoff-specific chains
        self.handoff_decision = dspy.ChainOfThought(HandoffDecision)
        self.handoff_protocol = dspy.ChainOfThought(HandoffProtocol)
        self.handoff_quality_assessor = dspy.ChainOfThought(HandoffQualityAssessment)
        # Enhanced workflow handoff decision
        if use_enhanced_signatures:
            self.workflow_handoff_decision = dspy.ChainOfThought(WorkflowHandoffDecision)

    def set_tool_registry(self, tool_registry: ToolRegistry) -> None:
        """Set the tool registry for tool-aware routing and analysis."""
        self.tool_registry = tool_registry

    def forward(
        self,
        task: str,
        team_capabilities: str,
        current_context: str = "",
        available_tools: str = "",
    ) -> dspy.Prediction:
        """Main forward method for DSPy compilation."""
        # Use provided available_tools or get from registry
        # (training examples provide this, runtime uses registry)
        if not available_tools and self.tool_registry:
            available_tools = self.tool_registry.get_tool_descriptions()

        # Analyze task first (prefer tool-aware analyzer when tools available)
        if available_tools and self.enable_tool_usage:
            self.tool_aware_analyzer(task=task, available_tools=available_tools)
        else:
            self.task_analyzer(task=task)

        # Route based on analysis and team (always pass tools for visibility).
        routing = self.task_router(
            task=task,
            team_capabilities=team_capabilities,
            available_tools=available_tools or "No tools available",
            current_context=current_context or "Initial task",
            handoff_history="",  # TaskRouting is now handoff-aware
            workflow_state=current_context or "Initial workflow state",
        )
        execution_mode = getattr(routing, "execution_mode", "delegated")
        assigned_to = getattr(routing, "assigned_to", "")
        subtasks_val = getattr(routing, "subtasks", "")
        confidence = getattr(
            routing,
            "confidence",
            getattr(routing, "routing_confidence", getattr(routing, "decision_confidence", "")),
        )

        self.execution_context.append(
            {
                "task": task,
                "assigned_to": assigned_to,
                "execution_mode": execution_mode,
                "confidence": confidence,
            }
        )
        if len(self.execution_context) > 100:
            self.execution_context = self.execution_context[-100:]

        # Return prediction object for compilation (retain subtasks for runtime use)
        return dspy.Prediction(
            assigned_to=assigned_to,
            execution_mode=execution_mode,
            subtasks=subtasks_val,
            confidence=confidence,
        )

    def decide_tools(
        self,
        task: str,
        team: dict[str, str] | None = None,
        current_context: str = "",
    ) -> dict[str, Any]:
        """
        Produce a lightweight, tool-aware plan for ReAct-style execution.

        Returns a compact plan:
          - tool_plan: ordered list of tool names (as list[str])
          - tool_goals: brief goal string for tool usage
          - latency_budget: one of low|medium|high
        """
        team_capabilities = ""
        if team:
            team_capabilities = "\n".join([f"{k}: {v}" for k, v in team.items()])

        available_tools = ""
        if self.tool_registry:
            available_tools = self.tool_registry.get_tool_descriptions()

        routing = self.task_router(
            task=task,
            team_capabilities=team_capabilities or "Unspecified team",
            available_tools=available_tools or "No tools available",
            current_context=current_context or "Initial task",
            handoff_history="",
            workflow_state=current_context or "Initial workflow state",
        )

        raw_plan = getattr(routing, "tool_plan", "") or ""
        # Normalize comma/newline separated into a clean list
        if isinstance(raw_plan, str):
            raw_plan_list = [p.strip() for p in raw_plan.replace("\n", ",").split(",") if p.strip()]
        elif isinstance(raw_plan, list | tuple):
            raw_plan_list = [str(p).strip() for p in raw_plan if str(p).strip()]
        else:
            raw_plan_list = []

        return {
            "tool_plan": raw_plan_list,
            "tool_goals": getattr(routing, "tool_goals", "") or "",
            "latency_budget": getattr(routing, "latency_budget", "") or "",
        }

    def analyze_task(
        self,
        task: str,
        use_tools: bool = True,
        *,
        perform_search: bool = True,
    ) -> dict[str, Any]:
        """
        Analyze task complexity and requirements.

        Args:
            task: Task to analyze
            use_tools: Whether to use tool-aware analysis and potentially invoke tools

        Returns:
            Dictionary with analysis results including tool requirements
        """
        # Get tool descriptions if registry is available
        available_tools = ""
        if self.tool_registry:
            available_tools = self.tool_registry.get_tool_descriptions()

        # Use tool-aware analysis if enabled and registry is available
        if use_tools and self.enable_tool_usage and self.tool_registry and available_tools:
            analysis = self.tool_aware_analyzer(task=task, available_tools=available_tools)

            # Check if web search is needed and perform it
            search_context = ""
            needs_search = False
            search_query = ""
            if hasattr(analysis, "needs_web_search") and analysis.needs_web_search:
                needs_search = analysis.needs_web_search.lower().strip() in (
                    "yes",
                    "true",
                    "1",
                    "y",
                )
                if needs_search and hasattr(analysis, "search_query") and analysis.search_query:
                    search_query = analysis.search_query.strip()
                    if search_query and perform_search:
                        # Perform search using tool registry
                        search_result = self._perform_web_search(search_query)
                        if search_result:
                            search_context = (
                                f"\n\nWeb search context for '{search_query}':\n{search_result}"
                            )

            # Parse tool requirements
            tool_requirements = []
            if hasattr(analysis, "tool_requirements") and analysis.tool_requirements:
                tool_requirements = self._parse_tool_requirements(analysis.tool_requirements)

            return {
                "complexity": analysis.complexity,
                "capabilities": self._parse_capabilities(analysis.required_capabilities),
                "tool_requirements": tool_requirements,
                "steps": int(analysis.estimated_steps) if analysis.estimated_steps.isdigit() else 3,
                "search_context": search_context,
                "needs_web_search": needs_search,
                "search_query": search_query,
            }
        else:
            # Fall back to standard analysis
            analysis = self.task_analyzer(task=task)

            # Parse tool requirements if present
            tool_requirements = []
            if hasattr(analysis, "tool_requirements") and analysis.tool_requirements:
                tool_requirements = self._parse_tool_requirements(analysis.tool_requirements)

            return {
                "complexity": analysis.complexity,
                "capabilities": self._parse_capabilities(analysis.required_capabilities),
                "tool_requirements": tool_requirements,
                "steps": int(analysis.estimated_steps) if analysis.estimated_steps.isdigit() else 3,
                "search_context": "",
                "needs_web_search": False,
                "search_query": "",
            }

    def _perform_web_search(self, query: str) -> str | None:
        """
        Perform web search using available tools.

        Note: This is a synchronous wrapper. For async tools, the caller
        should use the tool registry's execute_tool method directly.

        Args:
            query: Search query

        Returns:
            Search results or None if no search tool available
        """
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # Defer to async pathway when already in event loop context
                logger.debug(
                    "perform_web_search called from running event loop; returning None to avoid blocking."
                )
                return None
        except RuntimeError:
            # No running loop; safe to run coroutine synchronously
            return asyncio.run(self.perform_web_search_async(query))

        return None

    async def perform_web_search_async(self, query: str) -> str | None:
        """
        Perform web search using available tools asynchronously.

        Args:
            query: Search query

        Returns:
            Search results or None if no search tool available
        """
        if not self.tool_registry:
            return None

        # Find web search tools
        search_tools = self.tool_registry.get_tools_by_capability("web_search")
        if not search_tools:
            return None

        # Use the first available search tool
        tool = search_tools[0]
        if tool.tool_instance:
            try:
                # Check if the tool's run method is async or sync
                if asyncio.iscoroutinefunction(tool.tool_instance.run):  # type: ignore[attr-defined]
                    # Tool is async - await directly
                    result = await tool.tool_instance.run(query=query)  # type: ignore[attr-defined]
                else:
                    # Tool is sync - run in executor to avoid blocking event loop
                    try:
                        loop = asyncio.get_running_loop()
                        # Lambda ensures synchronous call happens in thread pool
                        result = await loop.run_in_executor(
                            None,
                            lambda: tool.tool_instance.run(query=query),  # type: ignore[attr-defined]
                        )
                    except RuntimeError:
                        # No event loop, run synchronously
                        result = tool.tool_instance.run(query=query)  # type: ignore[attr-defined]
                return str(result) if result else None
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Web search tool failed: %s", exc)
                return None

        return None

    def route_task(
        self, task: str, team: dict[str, str], context: str = "", handoff_history: str = ""
    ) -> RoutingDecision:
        """Intelligently route task to team members.

        Uses EnhancedTaskRouting if enabled for better workflow state awareness.
        """
        team_desc = "\n".join([f"{name}: {desc}" for name, desc in team.items()])

        # Get tool descriptions if registry is available
        available_tools = ""
        if self.tool_registry:
            available_tools = self.tool_registry.get_tool_descriptions()

        # Route using enhanced or standard routing signature
        if self.enhanced_routing_enabled:
            # Enhanced routing with workflow state awareness
            routing = self.task_router(
                task=task,
                team_capabilities=team_desc,
                available_tools=available_tools or "No tools available",
                current_context=context or "Initial task",
                handoff_history=handoff_history or "",
                workflow_state=context or "Initial workflow state",
            )
            # Extract enhanced fields if available
            handoff_strategy = getattr(routing, "handoff_strategy", "")
            workflow_gates = getattr(routing, "workflow_gates", "")
            # Store enhanced reasoning in execution context
            if handoff_strategy or workflow_gates:
                self.execution_context.append(
                    {
                        "routing_reasoning": {
                            "handoff_strategy": handoff_strategy,
                            "workflow_gates": workflow_gates,
                        }
                    }
                )
        else:
            # Standard routing
            routing = self.task_router(
                task=task,
                team_capabilities=team_desc,
                available_tools=available_tools or "No tools available",
                current_context=context or "Initial task",
                handoff_history=handoff_history or "",
            )

        exec_mode = getattr(routing, "execution_mode", "delegated")
        assigned_raw = getattr(routing, "assigned_to", "")
        subtasks_val = getattr(routing, "subtasks", "")
        confidence_raw = getattr(
            routing,
            "confidence",
            getattr(routing, "routing_confidence", getattr(routing, "decision_confidence", None)),
        )
        try:
            confidence_val = float(confidence_raw) if confidence_raw not in (None, "") else None
        except (TypeError, ValueError):
            confidence_val = None

        # ------------------------------------------------------------------
        # Normalise assigned agents against the known team.
        # DSPy may return free-form descriptions here (especially when
        # running without compiled examples), so we coerce the output
        # back to concrete agent IDs that exist in ``team``.
        # ------------------------------------------------------------------
        if isinstance(assigned_raw, str):
            assigned_str = assigned_raw
        elif isinstance(assigned_raw, list | tuple | set):
            assigned_str = ", ".join(str(a) for a in assigned_raw)
        else:
            assigned_str = str(assigned_raw or "")

        parsed_agents = self._parse_agents(assigned_str)

        team_keys = list(team.keys())
        team_keys_lower = {k.lower(): k for k in team_keys}

        normalised_agents: list[str] = []
        seen: set[str] = set()

        for candidate in parsed_agents:
            # Exact match
            if candidate in team:
                canonical = candidate
            else:
                cand_lower = candidate.lower()
                # Case-insensitive match
                canonical = team_keys_lower.get(cand_lower)
                if canonical is None:
                    # Fuzzy substring match (handles descriptions like
                    # "Researcher (primary)" or "primary work by the researcher").
                    for key in team_keys:
                        key_lower = key.lower()
                        if key_lower in cand_lower or cand_lower in key_lower:
                            canonical = key
                            break

            if canonical and canonical not in seen:
                normalised_agents.append(canonical)
                seen.add(canonical)

        # Fallback: if nothing matched, prefer a Researcher-like agent,
        # or the first team member as a safe default.
        if not normalised_agents:
            fallback = None
            for key in team_keys:
                if key.lower() == "researcher":
                    fallback = key
                    break
            if fallback is None and team_keys:
                fallback = team_keys[0]
            normalised_agents = [fallback] if fallback else []

        mode_enum = ExecutionMode.from_raw(exec_mode)

        # Delegated mode should always target a single agent.
        if mode_enum is ExecutionMode.DELEGATED and len(normalised_agents) > 1:
            normalised_agents = normalised_agents[:1]

        # Extract tool requirements from analysis if available using the
        # normalised agents list.
        tool_requirements_set = set()  # Use set for O(1) lookups instead of O(n) list
        if self.tool_registry:
            for agent_name in normalised_agents:
                agent_tools = self.tool_registry.get_agent_tools(agent_name)
                for tool_meta in agent_tools:
                    tool_requirements_set.add(tool_meta.name)

        decision = RoutingDecision(
            task=task,
            assigned_to=tuple(normalised_agents),
            mode=mode_enum,
            subtasks=tuple(self._parse_subtasks(subtasks_val)),
            tool_requirements=tuple(tool_requirements_set),
            confidence=confidence_val,
        )

        self.routing_history.append(decision)

        return decision

    def evaluate_progress(self, original_task: str, completed: str, status: str) -> dict[str, Any]:
        """Evaluate workflow progress and determine next steps."""

        evaluation = self.progress_evaluator(
            original_task=original_task, completed_work=completed, current_status=status
        )

        return {"action": evaluation.next_action, "feedback": evaluation.feedback}

    def assess_quality(
        self, requirements: str, results: str, quality_criteria: str | None = None
    ) -> dict[str, Any]:
        """Assess quality of final results.

        Uses JudgeEvaluation signature if enabled for structured quality assessment
        with task-specific criteria.

        Args:
            requirements: Original task requirements
            results: Results to evaluate
            quality_criteria: Optional task-specific quality criteria (used with JudgeEvaluation)

        Returns:
            Dictionary with quality assessment including score, missing elements, improvements
        """
        if self.enhanced_judge_enabled and quality_criteria:
            # Use enhanced judge evaluation with criteria
            assessment = self.judge_evaluator(
                task=requirements,
                result=results,
                quality_criteria=quality_criteria,
            )
            # Extract enhanced fields
            refinement_agent = getattr(assessment, "refinement_agent", "")
            refinement_needed = getattr(assessment, "refinement_needed", "no")
            # Store enhanced reasoning
            self.execution_context.append(
                {
                    "quality_reasoning": {
                        "refinement_agent": refinement_agent,
                        "refinement_needed": refinement_needed,
                        "criteria_used": quality_criteria,
                    }
                }
            )
            return {
                "score": self._parse_score(assessment.score),
                "missing": assessment.missing_elements,
                "improvements": assessment.required_improvements,
                "refinement_agent": refinement_agent,
                "refinement_needed": refinement_needed.lower() in ("yes", "true", "1", "y"),
            }
        else:
            # Use standard quality assessment
            if not hasattr(self, "quality_assessor"):
                # Fallback if enhanced mode but no criteria provided
                assessment = self.judge_evaluator(
                    task=requirements,
                    result=results,
                    quality_criteria=quality_criteria or "General quality criteria",
                )
                return {
                    "score": self._parse_score(assessment.score),
                    "missing": assessment.missing_elements,
                    "improvements": assessment.required_improvements,
                }
            assessment = self.quality_assessor(requirements=requirements, results=results)
            return {
                "score": self._parse_score(assessment.quality_score),
                "missing": assessment.missing_elements,
                "improvements": assessment.improvement_suggestions,
            }

    def get_execution_summary(self) -> dict[str, Any]:
        """Get summary of execution history with verbose reasoning traces.

        Returns a rich summary including:
        - Routing decisions and confidence scores
        - Tool usage statistics
        - Reasoning traces from enhanced signatures (if enabled)
        - Quality assessment reasoning
        """
        # Collect tool usage statistics
        tool_usage_stats: dict[str, int] = {}
        for routing in self.routing_history:
            for tool in routing.tool_requirements:
                tool_usage_stats[tool] = tool_usage_stats.get(tool, 0) + 1

        confidences = [
            decision.confidence
            for decision in self.routing_history
            if decision.confidence is not None
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None

        # Extract reasoning traces from execution context
        routing_reasoning = []
        quality_reasoning = []
        for ctx in self.execution_context:
            if isinstance(ctx, dict):
                if "routing_reasoning" in ctx:
                    routing_reasoning.append(ctx["routing_reasoning"])
                if "quality_reasoning" in ctx:
                    quality_reasoning.append(ctx["quality_reasoning"])

        summary = {
            "total_routings": len(self.routing_history),
            "routing_history": [decision.to_dict() for decision in self.routing_history],
            "execution_context": self.execution_context,
            "tool_usage_stats": tool_usage_stats,
            "average_routing_confidence": avg_confidence,
            "signatures_used": {
                "routing": (
                    "EnhancedTaskRouting" if self.enhanced_routing_enabled else "TaskRouting"
                ),
                "quality": (
                    "JudgeEvaluation" if self.enhanced_judge_enabled else "QualityAssessment"
                ),
            },
        }

        # Add reasoning traces if available
        if routing_reasoning:
            summary["routing_reasoning_traces"] = routing_reasoning
        if quality_reasoning:
            summary["quality_reasoning_traces"] = quality_reasoning

        return summary

    def _parse_capabilities(self, capabilities_str: str) -> list[str]:
        """Parse capabilities from DSPy output."""
        if not capabilities_str:
            return []
        return [cap.strip() for cap in capabilities_str.split(",") if cap.strip()]

    def _parse_agents(self, agents_str: str) -> list[str]:
        """Parse agent list from DSPy output.

        The routing signatures typically emit a comma-separated list of
        agent identifiers (e.g. ``\"Researcher, Analyst\"``), but when
        running without compiled examples the model may instead return
        longer natural-language descriptions with newlines. To keep
        parsing robust we treat commas, semicolons, and newlines as
        delimiters.
        """
        if not agents_str:
            return []
        normalized = agents_str.replace("\n", ",").replace(";", ",")
        return [agent.strip() for agent in normalized.split(",") if agent.strip()]

    def _parse_subtasks(self, subtasks_str: str) -> list[str]:
        """Parse subtasks from DSPy output."""
        if not subtasks_str:
            return []
        return [task.strip() for task in subtasks_str.split("\n") if task.strip()]

    def _parse_score(self, score_str: str) -> float:
        """Parse quality score from DSPy output."""
        try:
            # Extract numeric value from string like "8/10" or "8"
            if "/" in score_str:
                return float(score_str.split("/")[0])
            return float(score_str)
        except (ValueError, AttributeError):
            return 5.0  # Default middle score

    def _parse_tool_requirements(self, tool_requirements_str: str) -> list[str]:
        """Parse tool requirements from DSPy output."""
        if not tool_requirements_str:
            return []
        # Handle comma-separated or newline-separated lists
        requirements = tool_requirements_str.replace("\n", ",").split(",")
        return [req.strip() for req in requirements if req.strip()]
