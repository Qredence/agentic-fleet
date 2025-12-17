"""Prediction methods for DSPyReasoner.

This module contains the core prediction logic extracted from reasoner.py
to reduce its size and improve maintainability.
"""

from __future__ import annotations

from typing import Any

from ..utils.logger import setup_logger
from ..utils.telemetry import optional_span
from .reasoner_utils import (
    _format_team_description,
    is_simple_task,
    is_time_sensitive_task,
)

logger = setup_logger(__name__)


class PredictionMethods:
    """Core prediction methods for DSPyReasoner."""

    def __init__(self, reasoner):
        """Initialize with reference to parent reasoner."""
        self.reasoner = reasoner

    def select_workflow_mode(self, task: str) -> dict[str, str]:
        """Select the optimal workflow architecture for a task.

        Args:
            task: The user's task description

        Returns:
            Dictionary containing:
            - mode: 'handoff', 'standard', or 'fast_path'
            - reasoning: Why this mode was chosen
        """
        with optional_span("DSPyReasoner.select_workflow_mode", attributes={"task": task}):
            logger.info(f"Selecting workflow mode for task: {task[:100]}...")

            # Fast check for trivial tasks to avoid DSPy overhead
            if is_simple_task(task):
                return {
                    "mode": "fast_path",
                    "reasoning": "Trivial task detected via keyword matching.",
                }

            if not self.reasoner.strategy_selector:
                return {
                    "mode": "standard",
                    "reasoning": "Strategy selector not initialized (legacy mode).",
                }

            # Analyze complexity first
            analysis = self.analyze_task(task)
            complexity_desc = (
                f"Complexity: {analysis['complexity']}, "
                f"Steps: {analysis['estimated_steps']}, "
                f"Time Sensitive: {analysis['time_sensitive']}"
            )

            prediction = self.reasoner.strategy_selector(
                task=task, complexity_analysis=complexity_desc
            )

            return {
                "mode": getattr(prediction, "workflow_mode", "standard"),
                "reasoning": getattr(prediction, "reasoning", ""),
            }

    def analyze_task(
        self, task: str, use_tools: bool = False, perform_search: bool = False
    ) -> dict[str, Any]:
        """Analyze a task to understand its requirements and complexity.

        Args:
            task: The user's task description
            use_tools: Whether to allow tool usage during analysis (default: False)
            perform_search: Whether to perform web search during analysis (default: False)

        Returns:
            Dictionary containing analysis results (complexity, capabilities, etc.)
        """
        with optional_span("DSPyReasoner.analyze_task", attributes={"task": task}):
            logger.info(f"Analyzing task: {task[:100]}...")

            # Perform NLU analysis first
            intent_data = self.reasoner.nlu.classify_intent(
                task,
                possible_intents=[
                    "information_retrieval",
                    "content_creation",
                    "code_generation",
                    "data_analysis",
                    "planning",
                    "chat",
                ],
            )
            logger.info(f"NLU Intent: {intent_data['intent']} ({intent_data['confidence']})")

            # Extract common entities
            entities_data = self.reasoner.nlu.extract_entities(
                task,
                entity_types=[
                    "Person",
                    "Organization",
                    "Location",
                    "Date",
                    "Time",
                    "Product",
                    "Event",
                ],
            )
            if entities_data.get("entities"):
                logger.info(f"Entities: {entities_data['entities']}")

            if use_tools:
                # Add tool context to the analysis
                tool_context = self._get_tool_context()
                if tool_context:
                    prediction = self.reasoner.analyzer(task=task, available_tools=tool_context)
                else:
                    prediction = self.reasoner.analyzer(task=task)
            else:
                prediction = self.reasoner.analyzer(task=task)

            # Convert to dictionary format
            result = {
                "intent": intent_data["intent"],
                "intent_confidence": intent_data["confidence"],
                "complexity": prediction.complexity,
                "required_capabilities": self._parse_capabilities(prediction.required_capabilities),
                "estimated_steps": max(1, int(getattr(prediction, "estimated_steps", 1))),
                "preferred_tools": self._parse_tools(prediction.preferred_tools),
                "needs_web_search": getattr(prediction, "needs_web_search", False),
                "search_query": getattr(prediction, "search_query", ""),
                "time_sensitive": getattr(prediction, "time_sensitive", False)
                or is_time_sensitive_task(task),
                "reasoning": getattr(prediction, "reasoning", ""),
            }

            # Extract entities if available
            if entities_data.get("entities"):
                result["entities"] = entities_data["entities"]

            # Store in execution history
            self.reasoner._execution_history.append({"phase": "analysis", "result": result})

            return result

    def route_task(
        self,
        task: str,
        agents: dict[str, Any],
        context: str = "",
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Route a task to the appropriate agent(s).

        Args:
            task: The task to route
            agents: Dictionary mapping agent names to ChatAgent instances
            context: Optional execution context
            use_cache: Whether to use routing cache (default: True)

        Returns:
            Dictionary containing routing decision
        """
        from .reasoner_utils import _generate_cache_key

        with optional_span("DSPyReasoner.route_task", attributes={"task": task}):
            logger.info(f"Routing task: {task[:100]}...")

            # Generate team description for cache key
            team_desc = self._format_team_description(agents)
            cache_key = _generate_cache_key(task, team_desc)

            # Check cache
            if use_cache and self.reasoner.enable_routing_cache:
                cached = self.reasoner._get_cached_routing(cache_key)
                if cached is not None:
                    logger.info("Using cached routing decision")
                    return cached

            # Perform routing
            if self.reasoner.use_enhanced_signatures:
                result = self._route_with_enhanced_signatures(task, agents, context)
            else:
                result = self._route_with_standard_signatures(task, agents, context)

            # Cache result
            if use_cache and self.reasoner.enable_routing_cache:
                self.reasoner._cache_routing(cache_key, result)

            return result

    def _route_with_enhanced_signatures(
        self, task: str, agents: dict[str, Any], context: str
    ) -> dict[str, Any]:
        """Route task using enhanced signatures."""
        return self._route_internal(task, agents, context, use_typed=True)

    def _route_with_standard_signatures(
        self, task: str, agents: dict[str, Any], context: str
    ) -> dict[str, Any]:
        """Route task using standard signatures."""
        return self._route_internal(task, agents, context, use_typed=False)

    def _route_internal(
        self, task: str, agents: dict[str, Any], context: str, use_typed: bool
    ) -> dict[str, Any]:
        """Internal routing implementation that handles both typed and standard signatures.

        Args:
            task: The task to route
            agents: Available agents
            context: Additional context
            use_typed: Whether to use typed signatures (True) or standard signatures (False)

        Returns:
            Dictionary with routing information
        """
        team_desc = self._format_team_description(agents)

        # Determine strategy
        if self.reasoner.strategy_selector:
            strategy_pred = self.reasoner.strategy_selector(task=task, team_composition=team_desc)
            if use_typed:
                strategy = getattr(strategy_pred, "strategy", "standard")
            else:
                strategy = getattr(strategy_pred, "workflow_mode", "standard")
        else:
            strategy = "standard"

        # Get routing prediction
        routing_pred = self.reasoner.router(
            task=task,
            team=team_desc,
            context=context,
            current_date=self._get_current_date(),
        )

        # Build result based on signature type
        if use_typed and self.reasoner.use_typed_signatures:
            # Extract from typed output
            return {
                "assigned_to": routing_pred.assigned_to,
                "mode": routing_pred.execution_mode,
                "subtasks": routing_pred.subtasks,
                "tool_requirements": routing_pred.tool_requirements,
                "tool_plan": routing_pred.tool_plan,
                "tool_goals": routing_pred.tool_goals,
                "latency_budget": routing_pred.latency_budget,
                "handoff_strategy": routing_pred.handoff_strategy,
                "workflow_gates": routing_pred.workflow_gates,
                "reasoning": routing_pred.reasoning,
                "strategy": strategy,
            }
        else:
            # Standard output
            return {
                "assigned_to": routing_pred.assigned_to,
                "mode": routing_pred.mode,
                "subtasks": routing_pred.subtasks,
                "tool_requirements": routing_pred.tool_requirements,
                "reasoning": routing_pred.reasoning,
                "strategy": strategy,
            }

    def generate_simple_response(self, task: str) -> str:
        """Generate a direct response for simple tasks using the simple responder module.

        Args:
            task: Simple task query

        Returns:
            Direct response text
        """
        with optional_span("DSPyReasoner.generate_simple_response", attributes={"task": task}):
            logger.info(f"Simple response for: {task[:50]}...")
            try:
                prediction = self.reasoner.simple_responder(task=task)
                return getattr(prediction, "response", "")
            except Exception as e:
                logger.error(f"Simple response generation failed: {e}")
                return f"I encountered an error while generating a response: {e}"

    def assess_quality(self, task: str = "", result: str = "", **kwargs: Any) -> dict[str, Any]:
        """Assess the quality of a task result.

        Args:
            task: The original task (optional)
            result: The result to assess (optional)
            **kwargs: Additional parameters passed through

        Returns:
            Dictionary containing quality assessment
        """
        with optional_span("DSPyReasoner.assess_quality"):
            logger.info(f"Assessing quality for task: {task[:50]}...")

            if self.reasoner.use_typed_signatures:
                prediction = self.reasoner.quality_assessor(task=task, result=result, **kwargs)
                return {
                    "score": prediction.score,
                    "missing_elements": prediction.missing_elements,
                    "required_improvements": prediction.required_improvements,
                    "reasoning": prediction.reasoning,
                }
            else:
                prediction = self.reasoner.quality_assessor(task=task, result=result, **kwargs)
                return {
                    "score": prediction.score,
                    "missing_elements": prediction.missing_elements,
                    "required_improvements": prediction.required_improvements,
                    "reasoning": prediction.reasoning,
                }

    def evaluate_progress(self, task: str = "", result: str = "", **kwargs: Any) -> dict[str, Any]:
        """Evaluate progress toward task completion.

        Args:
            task: The original task (optional)
            result: Current result (optional)
            **kwargs: Additional parameters passed through

        Returns:
            Dictionary containing progress evaluation
        """
        with optional_span("DSPyReasoner.evaluate_progress"):
            logger.info(f"Evaluating progress for task: {task[:50]}...")

            prediction = self.reasoner.progress_evaluator(task=task, result=result, **kwargs)
            return {
                "state": prediction.state,
                "percentage_complete": prediction.percentage_complete,
                "remaining_work": prediction.remaining_work,
                "next_steps": prediction.next_steps,
                "confidence": prediction.confidence,
                "reasoning": prediction.reasoning,
            }

    def decide_tools(
        self,
        task: str,
        context: str = "",
        agents: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Decide which tools to use for a task.

        Args:
            task: The task requiring tools
            context: Optional context about the task
            agents: List of agents involved (optional)
            **kwargs: Additional parameters passed through

        Returns:
            Dictionary containing tool plan
        """
        with optional_span("DSPyReasoner.decide_tools", attributes={"task": task}):
            logger.info(f"Planning tools for task: {task[:50]}...")

            # Get available tools from registry
            tool_context = ""
            if self.reasoner.tool_registry:
                available_tools = self.reasoner.tool_registry.list_tools()
                if available_tools:
                    tool_context = "\n".join(
                        f"- {t.name}: {t.description}" for t in available_tools[:10]
                    )

            # Use typed or standard planner
            if self.reasoner.use_typed_signatures:
                prediction = self.reasoner.tool_planner(
                    task=task,
                    context=context,
                    available_tools=tool_context,
                    agent_assignments=", ".join(agents) if agents else "",
                    **kwargs,
                )
                return {
                    "selected_tools": prediction.selected_tools,
                    "tool_sequence": prediction.tool_sequence,
                    "tool_goals": prediction.tool_goals,
                    "estimated_duration": prediction.estimated_duration,
                    "alternatives": prediction.alternatives,
                    "reasoning": prediction.reasoning,
                }
            else:
                prediction = self.reasoner.tool_planner(
                    task=task,
                    context=context,
                    available_tools=tool_context,
                    agent_assignments=", ".join(agents) if agents else "",
                    **kwargs,
                )
                return {
                    "selected_tools": prediction.selected_tools,
                    "sequence": prediction.sequence,
                    "goals": prediction.goals,
                    "estimated_time": prediction.estimated_time,
                    "alternatives": prediction.alternatives,
                    "reasoning": prediction.reasoning,
                }

    # Helper methods
    def _get_current_date(self) -> str:
        """Get current date string for routing context."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d")

    def _format_team_description(self, agents: dict[str, Any]) -> str:
        """Format agent team description for routing prompts.

        Delegates to the standalone function in reasoner_utils.
        """
        return _format_team_description(agents)

    def _parse_capabilities(self, capabilities_str: str) -> list[str]:
        """Parse capabilities string into list."""
        if not capabilities_str:
            return []
        return [c.strip() for c in capabilities_str.split(",") if c.strip()]

    def _parse_tools(self, tools_str: str) -> list[str]:
        """Parse tools string into list."""
        if not tools_str:
            return []
        return [t.strip() for t in tools_str.split(",") if t.strip()]

    def _get_tool_context(self) -> str:
        """Get formatted tool context for analysis."""
        if not self.reasoner.tool_registry:
            return ""

        tools = self.reasoner.tool_registry.list_tools()
        if not tools:
            return ""

        return "\n".join(f"- {tool.name}: {tool.description}" for tool in tools[:5])
