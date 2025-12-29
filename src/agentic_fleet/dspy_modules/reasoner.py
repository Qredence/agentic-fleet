"""DSPy-powered reasoner for intelligent orchestration.

This module implements the DSPyReasoner, which uses DSPy's language model
programming capabilities to perform high-level cognitive tasks:
- Task Analysis: Decomposing complex requests
- Routing: Assigning tasks to the best agents
- Quality Assessment: Evaluating results against criteria
- Progress Tracking: Monitoring execution state
- Tool Planning: Deciding which tools to use

"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import dspy

from agentic_fleet.utils.infra.langfuse import create_dspy_span
from agentic_fleet.utils.infra.logging import setup_logger
from agentic_fleet.utils.infra.telemetry import optional_span

from ..workflows.exceptions import ToolError
from .reasoner_cache import RoutingCache
from .reasoner_modules import ModuleManager
from .reasoner_predictions import PredictionMethods
from .reasoner_utils import (
    _format_team_description,
    _generate_cache_key,
    get_configured_compiled_reasoner_path,
    get_reasoner_source_hash,
    is_simple_task,
    is_time_sensitive_task,
)

logger = setup_logger(__name__)


class DSPyReasoner(dspy.Module):
    """Reasoner that uses DSPy modules for orchestration decisions.

    Supports two signature modes:
    - Standard: Original DSPy signatures with individual output fields
    - Typed: Pydantic-based signatures for structured outputs (DSPy 3.x)

    The typed mode provides better output parsing reliability and validation.
    """

    def __init__(
        self,
        use_enhanced_signatures: bool = True,
        use_typed_signatures: bool = True,
        enable_routing_cache: bool = True,
        cache_ttl_seconds: int = 300,
        cache_max_entries: int = 1024,
    ) -> None:
        """
        Initialize the DSPyReasoner with configuration for signature mode and routing cache.

        Parameters:
            use_enhanced_signatures (bool): Enable enhanced routing that includes tool planning and richer outputs.
            use_typed_signatures (bool): Use Pydantic-typed signatures for structured outputs (DSPy 3.x).
            enable_routing_cache (bool): Enable in-memory caching of routing decisions to reduce repeated model calls.
            cache_ttl_seconds (int): Time-to-live for cached routing entries in seconds.
            cache_max_entries (int): Maximum number of cached routing entries to retain in memory.
        """
        super().__init__()
        self.use_enhanced_signatures = use_enhanced_signatures
        self.use_typed_signatures = use_typed_signatures
        self.enable_routing_cache = enable_routing_cache

        self._execution_history: list[dict[str, Any]] = []
        self.tool_registry: Any | None = None

        # Initialize ModuleManager for module initialization and caching
        self._module_manager = ModuleManager(
            use_enhanced_signatures=use_enhanced_signatures,
            use_typed_signatures=use_typed_signatures,
        )

        # Initialize RoutingCache for routing decisions
        self._routing_cache = RoutingCache(
            ttl_seconds=cache_ttl_seconds,
            max_size=max(1, int(cache_max_entries)),
        )

        # Initialize PredictionMethods for prediction delegation
        self._predictions = PredictionMethods(self)

    def _ensure_modules_initialized(self) -> None:
        """Lazily initialize DSPy modules via ModuleManager."""
        self._module_manager.ensure_modules_initialized()
        # Load compiled optimization if available
        self._load_compiled_module()

    def _load_compiled_module(self) -> None:
        """Attempt to load optimized prompt weights from disk."""
        compiled_path = get_configured_compiled_reasoner_path()
        meta_path = Path(f"{compiled_path}.meta")

        if compiled_path.exists():
            try:
                if meta_path.exists():
                    try:
                        meta = json.loads(meta_path.read_text())
                        expected_hash = meta.get("reasoner_source_hash")
                        current_hash = get_reasoner_source_hash()
                        if expected_hash and expected_hash != current_hash:
                            logger.info(
                                "Compiled reasoner ignored (source hash mismatch: %s != %s)",
                                expected_hash,
                                current_hash,
                            )
                            return
                    except Exception as exc:  # pragma: no cover - best-effort
                        logger.debug("Failed to read compiled reasoner metadata: %s", exc)

                logger.info(f"Loading compiled reasoner from {compiled_path}")
                self.load(str(compiled_path))
                logger.debug("Successfully loaded compiled DSPy prompts.")
            except Exception as e:
                logger.warning(f"Failed to load compiled reasoner: {e}")
        else:
            logger.debug(
                "No compiled reasoner found at %s. Using default zero-shot prompts.",
                compiled_path,
            )

    @property
    def event_narrator(self) -> dspy.Module:
        """Lazily initialized event narrator."""
        self._ensure_modules_initialized()
        return self._module_manager.event_narrator

    @event_narrator.setter
    def event_narrator(self, value: dspy.Module) -> None:
        """Allow setting event narrator."""
        self._module_manager.event_narrator = value

    def narrate_events(self, events: list[dict[str, Any]]) -> str:
        """Generate a narrative summary from workflow events.

        Args:
            events: List of event dictionaries.

        Returns:
            Narrative string.
        """
        with (
            create_dspy_span("narrate_events", module_name="event_narrator"),
            optional_span("DSPyReasoner.narrate_events"),
        ):
            if not events:
                return "No events to narrate."

            try:
                # The EventNarrator module's forward method takes 'events' list
                prediction = self.event_narrator(events=events)
                return getattr(prediction, "narrative", "")
            except Exception as e:
                logger.error(f"Event narration failed: {e}")
                return "Narrative generation unavailable."

    @property
    def analyzer(self) -> dspy.Module:
        """Provide lazy access to the task analyzer module."""
        self._ensure_modules_initialized()
        return self._module_manager.analyzer

    @analyzer.setter
    def analyzer(self, value: dspy.Module) -> None:
        """Allow setting analyzer (for compiled module loading)."""
        self._module_manager.analyzer = value

    @property
    def router(self) -> dspy.Module:
        """Lazily initialized task router."""
        self._ensure_modules_initialized()
        return self._module_manager.router

    @router.setter
    def router(self, value: dspy.Module) -> None:
        """Allow setting router (for compiled module loading)."""
        self._module_manager.router = value

    @property
    def strategy_selector(self) -> dspy.Module | None:
        """Lazily initialized strategy selector."""
        self._ensure_modules_initialized()
        return self._module_manager.strategy_selector

    @strategy_selector.setter
    def strategy_selector(self, value: dspy.Module | None) -> None:
        """Allow setting strategy selector (for compiled module loading)."""
        self._module_manager.strategy_selector = value

    @property
    def quality_assessor(self) -> dspy.Module:
        """Lazily initialized quality assessor."""
        self._ensure_modules_initialized()
        return self._module_manager.quality_assessor

    @quality_assessor.setter
    def quality_assessor(self, value: dspy.Module) -> None:
        """Allow setting quality assessor (for compiled module loading)."""
        self._module_manager.quality_assessor = value

    @property
    def progress_evaluator(self) -> dspy.Module:
        """Lazily initialized progress evaluator."""
        self._ensure_modules_initialized()
        return self._module_manager.progress_evaluator

    @progress_evaluator.setter
    def progress_evaluator(self, value: dspy.Module) -> None:
        """Allow setting progress evaluator (for compiled module loading)."""
        self._module_manager.progress_evaluator = value

    @property
    def tool_planner(self) -> dspy.Module:
        """Lazily initialized tool planner."""
        self._ensure_modules_initialized()
        return self._module_manager.tool_planner

    @tool_planner.setter
    def tool_planner(self, value: dspy.Module) -> None:
        """Allow setting tool planner (for compiled module loading)."""
        self._module_manager.tool_planner = value

    @property
    def simple_responder(self) -> dspy.Module:
        """Lazily initialized simple responder."""
        self._ensure_modules_initialized()
        return self._module_manager.simple_responder

    @simple_responder.setter
    def simple_responder(self, value: dspy.Module) -> None:
        """Allow setting simple responder (for compiled module loading)."""
        self._module_manager.simple_responder = value

    @property
    def group_chat_selector(self) -> dspy.Module:
        """Lazily initialized group chat selector."""
        self._ensure_modules_initialized()
        return self._module_manager.group_chat_selector

    @group_chat_selector.setter
    def group_chat_selector(self, value: dspy.Module) -> None:
        """Allow setting group chat selector (for compiled module loading)."""
        self._module_manager.group_chat_selector = value

    @property
    def nlu(self):
        """Lazily initialized NLU module."""
        self._ensure_modules_initialized()
        return self._module_manager.nlu

    @nlu.setter
    def nlu(self, value) -> None:
        """Allow setting NLU module."""
        self._module_manager.nlu = value

    def _robust_route(self, max_backtracks: int = 2, **kwargs) -> dspy.Prediction:
        """Execute routing with DSPy assertions."""
        # Call the router directly
        # We preserve the max_backtracks arg for interface compatibility
        with create_dspy_span("route_robustly", module_name="router"):
            prediction = self.router(**kwargs)

        # Basic assertion to ensure at least one agent is assigned
        if self.use_enhanced_signatures:
            import contextlib

            from ..utils.models import ExecutionMode, RoutingDecision
            from .assertions import validate_routing_decision

            with contextlib.suppress(Exception):
                suggest_fn = getattr(dspy, "Suggest", None)
                if callable(suggest_fn):
                    # Basic check
                    suggest_fn(
                        len(getattr(prediction, "assigned_to", [])) > 0,
                        "At least one agent must be assigned to the task.",
                    )

                    # Advanced validation
                    task = kwargs.get("task", "")
                    decision = RoutingDecision(
                        task=task,
                        assigned_to=tuple(getattr(prediction, "assigned_to", [])),
                        mode=ExecutionMode.from_raw(
                            getattr(prediction, "execution_mode", "delegated")
                        ),
                        subtasks=tuple(getattr(prediction, "subtasks", [])),
                        tool_requirements=tuple(getattr(prediction, "tool_requirements", [])),
                    )
                    validate_routing_decision(decision, task)

        return prediction

    def forward(
        self,
        task: str,
        team: str = "",
        team_capabilities: str = "",
        available_tools: str = "",
        context: str = "",
        current_context: str = "",
        **kwargs: Any,
    ) -> dspy.Prediction:
        """Forward pass for DSPy optimization (routing focus).

        This method allows the supervisor to be optimized as a DSPy module,
        mapping training example fields to the internal router's signature.
        """
        # Handle field aliases from examples vs signature
        actual_team = team_capabilities or team
        actual_context = current_context or context

        if self.use_enhanced_signatures:
            return self._robust_route(
                task=task,
                team_capabilities=actual_team,
                available_tools=available_tools,
                current_context=actual_context,
                handoff_history=kwargs.get("handoff_history", ""),
                workflow_state=kwargs.get("workflow_state", "Active"),
            )
        else:
            return self._robust_route(
                task=task,
                team=actual_team,
                context=actual_context,
                current_date=kwargs.get("current_date", ""),
            )

    def predictors(self) -> list[dspy.Module]:
        """Return list of predictors for GEPA optimization."""
        return self._module_manager.get_predictors()

    def named_predictors(self) -> list[tuple[str, dspy.Module]]:
        """Return predictor modules with stable names for GEPA."""
        return self._module_manager.get_named_predictors()

    def set_tool_registry(self, tool_registry: Any) -> None:
        """Attach a tool registry to the supervisor."""
        self.tool_registry = tool_registry

    def set_decision_modules(
        self,
        routing_module: Any | None = None,
        quality_module: Any | None = None,
        tool_planning_module: Any | None = None,
    ) -> None:
        """Inject external decision modules from Phase 2 integration.

        This allows the workflow to use preloaded, compiled decision modules
        from app.state instead of the reasoner's internal modules.

        Args:
            routing_module: Preloaded routing decision module
            quality_module: Preloaded quality assessment module
            tool_planning_module: Preloaded tool planning module
        """
        if routing_module is not None:
            self._module_manager.router = routing_module
            logger.debug("Injected external routing decision module")
        if quality_module is not None:
            self._module_manager.quality_assessor = quality_module
            logger.debug("Injected external quality assessment module")
        if tool_planning_module is not None:
            self._module_manager.tool_planner = tool_planning_module
            logger.debug("Injected external tool planning module")

    def select_workflow_mode(self, task: str) -> dict[str, str]:
        """Select the optimal workflow architecture for a task."""
        return self._predictions.select_workflow_mode(task)

    def analyze_task(
        self, task: str, use_tools: bool = False, perform_search: bool = False
    ) -> dict[str, Any]:
        """Analyze a task to understand its requirements and complexity."""
        result = self._predictions.analyze_task(
            task, use_tools=use_tools, perform_search=perform_search
        )
        # Map result to expected format (add missing fields for backward compatibility)
        if "capabilities" not in result:
            result["capabilities"] = result.get("required_capabilities", [])
        if "steps" not in result:
            result["steps"] = result.get("estimated_steps", 1)
        if "search_context" not in result:
            result["search_context"] = result.get("search_query", "")
        if "urgency" not in result:
            result["urgency"] = "medium"
        return result

    def route_task(
        self,
        task: str,
        team: dict[str, str],
        context: str = "",
        handoff_history: list[dict[str, Any]] | None = None,
        current_date: str | None = None,
        required_capabilities: list[str] | None = None,
        max_backtracks: int = 2,
        skip_cache: bool = False,
    ) -> dict[str, Any]:
        """
        Decide and return an orchestrated routing for a task, including assigned agents, execution mode, subtasks, and tool plan.

        Parameters:
            task (str): The task description to route.
            team (dict[str, str]): Mapping of agent names to their descriptions.
            context (str, optional): Current contextual information to inform routing.
            handoff_history (list[dict[str, Any]] | None, optional): Chronological handoff records to include in routing context.
            current_date (str | None, optional): Current date in YYYY-MM-DD format; used when time/context sensitivity matters.
            required_capabilities (list[str] | None, optional): Capabilities to prioritize when selecting agents.
            max_backtracks (int, optional): Maximum number of router assertion retries.
            skip_cache (bool, optional): If true, bypasses the routing cache and forces a fresh routing decision.

        Returns:
            dict[str, Any]: A routing decision containing at least:
                - "task": original task string.
                - "assigned_to": list of agent names selected for the task.
                - "mode": execution mode (e.g., "delegated", "parallel").
                - "subtasks": list of subtasks or the original task if none were produced.
                - "tool_plan" / "tool_requirements": ordered tools planned for execution (may be empty).
                - "tool_goals": goals for tool usage when available.
                - "latency_budget": latency expectation (e.g., "low", "medium").
                - "handoff_strategy": handoff guidance when present.
                - "workflow_gates": workflow gate information when present.
                - "reasoning": textual reasoning for the decision.

        Notes:
            - Simple/heartbeat tasks are routed directly to the "Writer" agent when present.
            - Time-sensitive tasks prefer the configured web-search tool (e.g., Tavily); when used, the "Researcher" role is prioritized and the tool is inserted into the tool plan.
            - When routing cache is enabled, results may be returned from or stored in the cache unless `skip_cache` is true.
        """
        with (
            create_dspy_span("route_task", module_name="router"),
            optional_span("DSPyReasoner.route_task", attributes={"task": task}),
        ):
            from datetime import datetime

            logger.info(f"Routing task: {task[:100]}...")

            # Check cache first (unless skipped or simple task)
            if not skip_cache and self.enable_routing_cache:
                team_desc = _format_team_description(team)
                cache_key = _generate_cache_key(task, team_desc)
                cached_result = self._routing_cache.get(cache_key)
                if cached_result is not None:
                    return cached_result

            if is_simple_task(task):
                if "Writer" in team:
                    logger.info(
                        "Detected simple/heartbeat task; routing directly to Writer (delegated)."
                    )
                    return {
                        "task": task,
                        "assigned_to": ["Writer"],
                        "mode": "delegated",
                        "subtasks": [task],
                        "tool_plan": [],
                        "tool_requirements": [],
                        "tool_goals": "Direct acknowledgment only",
                        "latency_budget": "low",
                        "handoff_strategy": "",
                        "workflow_gates": "",
                        "reasoning": "Simple/heartbeat task → route to Writer only",
                    }
                else:
                    logger.warning(
                        "Simple/heartbeat task detected, but 'Writer' agent is not present in the team. Falling back to standard routing."
                    )

            # Format team description using utility function
            team_str = _format_team_description(team)

            # Prefer real tool registry descriptions over generic team info
            available_tools = team_str
            if self.tool_registry:
                available_tools = self.tool_registry.get_tool_descriptions()

            # Detect time sensitivity to force web search usage
            time_sensitive = is_time_sensitive_task(task)
            preferred_web_tool = self._preferred_web_tool()

            if current_date is None:
                current_date = datetime.now().strftime("%Y-%m-%d")

            # Enhance context with required capabilities if provided
            enhanced_context = context
            if required_capabilities:
                caps_str = ", ".join(required_capabilities)
                if enhanced_context:
                    enhanced_context += (
                        f"\n\nFocus on agents matching these capabilities: {caps_str}"
                    )
                else:
                    enhanced_context = f"Focus on agents matching these capabilities: {caps_str}"

            if time_sensitive:
                freshness_note = (
                    "Task is time-sensitive: MUST use Tavily search tool if available."
                    if preferred_web_tool
                    else "Task is time-sensitive: no Tavily tool detected, reason carefully."
                )
                enhanced_context = (
                    f"{enhanced_context}\n{freshness_note}" if enhanced_context else freshness_note
                )

            if self.use_enhanced_signatures:
                # Convert handoff history to string if provided
                handoff_history_str = ""
                if handoff_history:
                    handoff_history_str = "\n".join(
                        [
                            f"{h.get('source')} -> {h.get('target')}: {h.get('reason')}"
                            for h in handoff_history
                        ]
                    )

                prediction = self._robust_route(
                    task=task,
                    team_capabilities=team_str,
                    available_tools=available_tools,
                    current_context=enhanced_context,
                    handoff_history=handoff_history_str,
                    workflow_state="Active",  # Default state
                )

                # Extract routing decision - handles both typed and standard signatures
                decision_data = self._extract_typed_routing_decision(prediction)

                tool_plan = list(decision_data.get("tool_plan", []))
                assigned_to = list(decision_data.get("assigned_to", []))
                execution_mode = decision_data.get("execution_mode", "delegated")
                subtasks = list(decision_data.get("subtasks", [task])) or [task]

                # Enforce web search for time-sensitive tasks when available
                if time_sensitive and preferred_web_tool:
                    if preferred_web_tool not in tool_plan:
                        tool_plan = [preferred_web_tool, *tool_plan]
                    if "Researcher" not in assigned_to:
                        assigned_to = (
                            ["Researcher", *assigned_to] if assigned_to else ["Researcher"]
                        )
                    if execution_mode == "delegated" and len(assigned_to) > 1:
                        execution_mode = "parallel"
                    if subtasks:
                        subtasks = [s or task for s in subtasks]
                    reasoning_note = "Time-sensitive → routed with Tavily web search"
                elif time_sensitive and not preferred_web_tool:
                    reasoning_note = "Time-sensitive but Tavily tool unavailable"
                else:
                    reasoning_note = ""

                reasoning_text = decision_data.get("reasoning", "")
                if reasoning_note:
                    reasoning_text = (str(reasoning_text) + "\n" + reasoning_note).strip()

                result = {
                    "task": task,
                    "assigned_to": assigned_to,
                    "mode": execution_mode,
                    "subtasks": subtasks,
                    "tool_plan": tool_plan,
                    "tool_requirements": tool_plan,  # Map for backward compatibility
                    "tool_goals": decision_data.get("tool_goals", ""),
                    "latency_budget": decision_data.get("latency_budget", "medium"),
                    "handoff_strategy": decision_data.get("handoff_strategy", ""),
                    "workflow_gates": decision_data.get("workflow_gates", ""),
                    "reasoning": reasoning_text,
                }

                # Cache the result
                if self.enable_routing_cache and not skip_cache:
                    # Format team description for cache key (consistent with PredictionMethods)
                    team_desc = _format_team_description(team)
                    cache_key = _generate_cache_key(task, team_desc)
                    self._routing_cache.set(cache_key, result)

                return result

            else:
                prediction = self._robust_route(
                    max_backtracks=max_backtracks,
                    task=task,
                    team=team_str,
                    context=enhanced_context,
                    current_date=current_date,
                )

                assigned_to = list(getattr(prediction, "assigned_to", []))
                mode = getattr(prediction, "mode", "delegated")
                subtasks = getattr(prediction, "subtasks", [task])
                tool_requirements = list(getattr(prediction, "tool_requirements", []))

                if time_sensitive and preferred_web_tool:
                    if preferred_web_tool not in tool_requirements:
                        tool_requirements.append(preferred_web_tool)
                    if "Researcher" not in assigned_to:
                        assigned_to = (
                            ["Researcher", *assigned_to] if assigned_to else ["Researcher"]
                        )
                    if mode == "delegated" and len(assigned_to) > 1:
                        mode = "parallel"
                    if subtasks:
                        subtasks = [s or task for s in subtasks]
                    reasoning_text = getattr(prediction, "reasoning", "")
                    reasoning_text = (reasoning_text + "\nTime-sensitive → Tavily required").strip()
                else:
                    reasoning_text = getattr(prediction, "reasoning", "")

                return {
                    "task": task,
                    "assigned_to": assigned_to,
                    "mode": mode,
                    "subtasks": subtasks,
                    "tool_requirements": tool_requirements,
                    "reasoning": reasoning_text,
                }

    def select_next_speaker(
        self, history: str, participants: str, last_speaker: str
    ) -> dict[str, str]:
        """Select the next speaker in a group chat.

        Args:
            history: The conversation history
            participants: List of participants and their roles
            last_speaker: The name of the last speaker

        Returns:
            Dictionary containing next_speaker and reasoning
        """
        with (
            create_dspy_span("select_next_speaker", module_name="group_chat_selector"),
            optional_span("DSPyReasoner.select_next_speaker"),
        ):
            logger.info("Selecting next speaker...")
            prediction = self.group_chat_selector(
                history=history, participants=participants, last_speaker=last_speaker
            )
            return {
                "next_speaker": getattr(prediction, "next_speaker", "TERMINATE"),
                "reasoning": getattr(prediction, "reasoning", ""),
            }

    def generate_simple_response(self, task: str) -> str:
        """Generate a direct response for a simple task."""
        return self._predictions.generate_simple_response(task)

    def assess_quality(self, task: str = "", result: str = "", **kwargs: Any) -> dict[str, Any]:
        """Assess the quality of a task result."""
        result_dict = self._predictions.assess_quality(task=task, result=result, **kwargs)
        # Map to expected format for backward compatibility
        return {
            "score": result_dict.get("score", 0.0),
            "missing": result_dict.get("missing_elements", ""),
            "improvements": result_dict.get("required_improvements", ""),
            "reasoning": result_dict.get("reasoning", ""),
        }

    def evaluate_progress(self, task: str = "", result: str = "", **kwargs: Any) -> dict[str, Any]:
        """Evaluate progress and decide next steps (complete or refine)."""
        result_dict = self._predictions.evaluate_progress(task=task, result=result, **kwargs)
        # Map to expected format for backward compatibility
        # Map "state" to "action" and "remaining_work" to "feedback"
        state = result_dict.get("state", "complete")
        # Convert state to action format if needed
        action = state if state in ("complete", "refine", "continue") else "complete"
        return {
            "action": action,
            "feedback": result_dict.get("remaining_work", ""),
            "reasoning": result_dict.get("reasoning", ""),
        }

    def decide_tools(
        self, task: str, team: dict[str, str], current_context: str = ""
    ) -> dict[str, Any]:
        """Decide which tools to use for a task (ReAct-style planning)."""
        agents_list = list(team.keys())
        result = self._predictions.decide_tools(
            task=task, context=current_context, agents=agents_list
        )
        # Map to expected format for backward compatibility
        return {
            "tool_plan": result.get("selected_tools", []),
            "reasoning": result.get("reasoning", ""),
        }

    async def perform_web_search_async(self, query: str, timeout: float = 12.0) -> str:
        """Execute the preferred web-search tool asynchronously."""

        if not query:
            return ""

        tool_name = self._preferred_web_tool()
        if not tool_name or not self.tool_registry:
            raise ToolError("No web search tool available", tool_name=tool_name or "unknown")

        try:
            result = await asyncio.wait_for(
                self.tool_registry.execute_tool(tool_name, query=query),
                timeout=timeout,
            )
        except TimeoutError:
            raise
        except Exception as exc:
            raise ToolError(
                f"Web search tool '{tool_name}' failed: {exc}",
                tool_name=tool_name,
                tool_args={"query": query},
            ) from exc

        if result is None:
            raise ToolError(
                "Web search returned empty result",
                tool_name=tool_name,
                tool_args={"query": query},
            )

        return str(result)

    def get_execution_summary(self) -> dict[str, Any]:
        """Provide a brief summary of the reasoner's execution state."""
        cache_stats = self._routing_cache.get_stats()
        return {
            "history_count": len(self._execution_history),
            "routing_cache_size": cache_stats.get("size", 0),
            "cache_hits": cache_stats.get("hits", 0),
            "cache_misses": cache_stats.get("misses", 0),
            "cache_hit_rate": cache_stats.get("hit_rate", 0.0),
        }

    # --- Cache management ---

    def _get_cache_key(self, task: str, team_key: str) -> str:
        """
        Create a cache key from task and team key.

        DEPRECATED: Use _generate_cache_key from reasoner_utils instead.
        Kept for backward compatibility with tests.

        Note: Returns full MD5 hash, not truncated to 16 chars like old implementation.
        """
        key = _generate_cache_key(task, team_key)
        # Truncate to 16 chars for backward compatibility with tests
        return key[:16] if len(key) > 16 else key

    def _get_cached_routing(self, cache_key: str) -> dict[str, Any] | None:
        """
        Get cached routing decision.

        DEPRECATED: Use self._routing_cache.get() directly.
        Kept for backward compatibility with tests.
        """
        if not self.enable_routing_cache:
            return None
        return self._routing_cache.get(cache_key)

    def _cache_routing(self, cache_key: str, result: dict[str, Any]) -> None:
        """
        Store routing decision in cache.

        DEPRECATED: Use self._routing_cache.set() directly.
        Kept for backward compatibility with tests.
        """
        if not self.enable_routing_cache:
            return
        self._routing_cache.set(cache_key, result)

    def clear_routing_cache(self) -> None:
        """Clear the routing cache."""
        self._routing_cache.clear()
        logger.debug("Routing cache cleared")

    @property
    def cache_ttl_seconds(self) -> int:
        """Get cache TTL in seconds."""
        return self._routing_cache.ttl_seconds

    @cache_ttl_seconds.setter
    def cache_ttl_seconds(self, value: int) -> None:
        """Set cache TTL in seconds (creates new cache instance)."""
        max_size = self._routing_cache.max_size
        self._routing_cache = RoutingCache(ttl_seconds=value, max_size=max_size)

    def _extract_typed_routing_decision(self, prediction: Any) -> dict[str, Any]:
        """
        Extract a plain dict of routing decision fields from a DSPy prediction that may use typed (Pydantic) signatures.

        If typed signatures are enabled, we expect a typed `decision` (Pydantic model) and serialize it to a dict (supports Pydantic v2 `model_dump()` and v1 `dict()`). If the prediction is legacy/untagged, we fall back to reading routing fields directly from the top-level prediction object.

        Parameters:
            prediction (Any): DSPy prediction object which may contain a typed `decision` attribute or top-level routing fields.

        Returns:
            dict[str, Any]: A dictionary with these routing fields:
                - assigned_to: list of assignees
                - execution_mode: execution mode string (default "delegated")
                - subtasks: list of subtasks
                - tool_requirements: list of tool requirement descriptors
                - tool_plan: list describing planned tool usage
                - tool_goals: tool goals string
                - latency_budget: latency preference (default "medium")
                - handoff_strategy: handoff strategy string
                - workflow_gates: workflow gate information
                - reasoning: human-readable reasoning or explanation
        """

        def _extract_from_decision(decision_obj: Any) -> dict[str, Any]:
            if isinstance(decision_obj, dict):
                return decision_obj
            if hasattr(decision_obj, "model_dump"):
                return decision_obj.model_dump()
            if hasattr(decision_obj, "dict"):
                return decision_obj.dict()
            return {
                "assigned_to": getattr(decision_obj, "assigned_to", []),
                "execution_mode": getattr(decision_obj, "execution_mode", "delegated"),
                "subtasks": getattr(decision_obj, "subtasks", []),
                "tool_requirements": getattr(decision_obj, "tool_requirements", []),
                "tool_plan": getattr(decision_obj, "tool_plan", []),
                "tool_goals": getattr(decision_obj, "tool_goals", ""),
                "latency_budget": getattr(decision_obj, "latency_budget", "medium"),
                "handoff_strategy": getattr(decision_obj, "handoff_strategy", ""),
                "workflow_gates": getattr(decision_obj, "workflow_gates", ""),
                "reasoning": getattr(decision_obj, "reasoning", ""),
            }

        if self.use_typed_signatures:
            decision = getattr(prediction, "decision", None)
            if decision is not None:
                return _extract_from_decision(decision)

        return {
            "assigned_to": list(getattr(prediction, "assigned_to", [])),
            "execution_mode": getattr(prediction, "execution_mode", "delegated"),
            "subtasks": list(getattr(prediction, "subtasks", [])),
            "tool_requirements": list(getattr(prediction, "tool_requirements", [])),
            "tool_plan": list(getattr(prediction, "tool_plan", [])),
            "tool_goals": getattr(prediction, "tool_goals", ""),
            "latency_budget": getattr(prediction, "latency_budget", "medium"),
            "handoff_strategy": getattr(prediction, "handoff_strategy", ""),
            "workflow_gates": getattr(prediction, "workflow_gates", ""),
            "reasoning": getattr(prediction, "reasoning", ""),
        }

    # --- Internal helpers ---

    def _preferred_web_tool(self) -> str | None:
        """Return the preferred web-search tool name if available."""

        if not self.tool_registry:
            return None

        web_tools = self.tool_registry.get_tools_by_capability("web_search")
        if not web_tools:
            return None

        # Prefer Tavily naming when present
        for tool in web_tools:
            if tool.name.lower().startswith("tavily"):
                return tool.name

        return web_tools[0].name
