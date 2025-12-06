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
from typing import Any

import dspy

from ..utils.logger import setup_logger
from ..utils.telemetry import optional_span
from ..workflows.exceptions import ToolError
from ..workflows.helpers import is_simple_task, is_time_sensitive_task
from .nlu import DSPyNLU, get_nlu_module
from .signatures import (
    EnhancedTaskRouting,
    GroupChatSpeakerSelection,
    ProgressEvaluation,
    QualityAssessment,
    SimpleResponse,
    TaskAnalysis,
    TaskRouting,
    ToolPlan,
    WorkflowStrategy,
)

logger = setup_logger(__name__)


# Module-level cache for DSPy module instances (stateless, can be shared)
_MODULE_CACHE: dict[str, dspy.Module] = {}


class DSPyReasoner(dspy.Module):
    """Reasoner that uses DSPy modules for orchestration decisions."""

    def __init__(self, use_enhanced_signatures: bool = True) -> None:
        """Initialize the DSPy reasoner.

        Args:
            use_enhanced_signatures: Whether to use the new typed signatures (default: True)
        """
        super().__init__()
        self.use_enhanced_signatures = use_enhanced_signatures
        self._execution_history: list[dict[str, Any]] = []
        self._modules_initialized = False
        self.tool_registry: Any | None = None

        # Placeholders for lazy-initialized modules
        self._analyzer: dspy.Module | None = None
        self._router: dspy.Module | None = None
        self._strategy_selector: dspy.Module | None = None
        self._quality_assessor: dspy.Module | None = None
        self._progress_evaluator: dspy.Module | None = None
        self._tool_planner: dspy.Module | None = None
        self._simple_responder: dspy.Module | None = None
        self._group_chat_selector: dspy.Module | None = None
        self._nlu: DSPyNLU | None = None

    def _ensure_modules_initialized(self) -> None:
        """Lazily initialize DSPy modules on first use.

        Only initializes modules that haven't been manually set (e.g., via setters
        for testing or loading compiled modules).
        """
        # Backward compatibility: compiled supervisors pickled before these fields
        # existed won't have them set on load.
        if not hasattr(self, "_modules_initialized"):
            self._modules_initialized = False
        if not hasattr(self, "_execution_history"):
            self._execution_history = []

        # Ensure lazy module placeholders exist for deserialized objects
        for attr in (
            "_analyzer",
            "_router",
            "_strategy_selector",
            "_quality_assessor",
            "_progress_evaluator",
            "_tool_planner",
            "_simple_responder",
            "_group_chat_selector",
            "_nlu",
        ):
            if not hasattr(self, attr):
                setattr(self, attr, None)

        if self._modules_initialized:
            return

        global _MODULE_CACHE

        # Use cached modules if available (DSPy modules are stateless)
        cache_key_prefix = "enhanced" if self.use_enhanced_signatures else "standard"

        # Only initialize if not already set (allows mocking in tests)
        # NLU
        if self._nlu is None:
            self._nlu = get_nlu_module()

        # Analyzer
        if self._analyzer is None:
            analyzer_key = f"{cache_key_prefix}_analyzer"
            if analyzer_key not in _MODULE_CACHE:
                _MODULE_CACHE[analyzer_key] = dspy.ChainOfThought(TaskAnalysis)
            self._analyzer = _MODULE_CACHE[analyzer_key]

        # Router and strategy selector
        if self._router is None:
            if self.use_enhanced_signatures:
                router_key = f"{cache_key_prefix}_router"
                if router_key not in _MODULE_CACHE:
                    _MODULE_CACHE[router_key] = dspy.Predict(EnhancedTaskRouting)
                self._router = _MODULE_CACHE[router_key]

                if self._strategy_selector is None:
                    strategy_key = f"{cache_key_prefix}_strategy"
                    if strategy_key not in _MODULE_CACHE:
                        _MODULE_CACHE[strategy_key] = dspy.ChainOfThought(WorkflowStrategy)
                    self._strategy_selector = _MODULE_CACHE[strategy_key]
            else:
                router_key = f"{cache_key_prefix}_router"
                if router_key not in _MODULE_CACHE:
                    _MODULE_CACHE[router_key] = dspy.Predict(TaskRouting)
                self._router = _MODULE_CACHE[router_key]

        # Quality assessor
        if self._quality_assessor is None:
            qa_key = "quality_assessor"
            if qa_key not in _MODULE_CACHE:
                _MODULE_CACHE[qa_key] = dspy.ChainOfThought(QualityAssessment)
            self._quality_assessor = _MODULE_CACHE[qa_key]

        # Progress evaluator
        if self._progress_evaluator is None:
            pe_key = "progress_evaluator"
            if pe_key not in _MODULE_CACHE:
                _MODULE_CACHE[pe_key] = dspy.ChainOfThought(ProgressEvaluation)
            self._progress_evaluator = _MODULE_CACHE[pe_key]

        # Tool planner
        if self._tool_planner is None:
            tp_key = "tool_planner"
            if tp_key not in _MODULE_CACHE:
                _MODULE_CACHE[tp_key] = dspy.ChainOfThought(ToolPlan)
            self._tool_planner = _MODULE_CACHE[tp_key]

        # Simple responder - use Predict for faster response (no CoT needed)
        if self._simple_responder is None:
            sr_key = "simple_responder"
            if sr_key not in _MODULE_CACHE:
                _MODULE_CACHE[sr_key] = dspy.Predict(SimpleResponse)
            self._simple_responder = _MODULE_CACHE[sr_key]

        # Group chat selector
        if self._group_chat_selector is None:
            gc_key = "group_chat_selector"
            if gc_key not in _MODULE_CACHE:
                _MODULE_CACHE[gc_key] = dspy.ChainOfThought(GroupChatSpeakerSelection)
            self._group_chat_selector = _MODULE_CACHE[gc_key]

        self._modules_initialized = True
        logger.debug("DSPy modules initialized (lazy)")

    @property
    def analyzer(self) -> dspy.Module:
        """Lazily initialized task analyzer."""
        self._ensure_modules_initialized()
        return self._analyzer  # type: ignore[return-value]

    @analyzer.setter
    def analyzer(self, value: dspy.Module) -> None:
        """Allow setting analyzer (for compiled module loading)."""
        self._analyzer = value

    @property
    def router(self) -> dspy.Module:
        """Lazily initialized task router."""
        self._ensure_modules_initialized()
        return self._router  # type: ignore[return-value]

    @router.setter
    def router(self, value: dspy.Module) -> None:
        """Allow setting router (for compiled module loading)."""
        self._router = value

    @property
    def strategy_selector(self) -> dspy.Module | None:
        """Lazily initialized strategy selector."""
        self._ensure_modules_initialized()
        return self._strategy_selector

    @strategy_selector.setter
    def strategy_selector(self, value: dspy.Module | None) -> None:
        """Allow setting strategy selector (for compiled module loading)."""
        self._strategy_selector = value

    @property
    def quality_assessor(self) -> dspy.Module:
        """Lazily initialized quality assessor."""
        self._ensure_modules_initialized()
        return self._quality_assessor  # type: ignore[return-value]

    @quality_assessor.setter
    def quality_assessor(self, value: dspy.Module) -> None:
        """Allow setting quality assessor (for compiled module loading)."""
        self._quality_assessor = value

    @property
    def progress_evaluator(self) -> dspy.Module:
        """Lazily initialized progress evaluator."""
        self._ensure_modules_initialized()
        return self._progress_evaluator  # type: ignore[return-value]

    @progress_evaluator.setter
    def progress_evaluator(self, value: dspy.Module) -> None:
        """Allow setting progress evaluator (for compiled module loading)."""
        self._progress_evaluator = value

    @property
    def tool_planner(self) -> dspy.Module:
        """Lazily initialized tool planner."""
        self._ensure_modules_initialized()
        return self._tool_planner  # type: ignore[return-value]

    @tool_planner.setter
    def tool_planner(self, value: dspy.Module) -> None:
        """Allow setting tool planner (for compiled module loading)."""
        self._tool_planner = value

    @property
    def simple_responder(self) -> dspy.Module:
        """Lazily initialized simple responder."""
        self._ensure_modules_initialized()
        return self._simple_responder  # type: ignore[return-value]

    @simple_responder.setter
    def simple_responder(self, value: dspy.Module) -> None:
        """Allow setting simple responder (for compiled module loading)."""
        self._simple_responder = value

    @property
    def group_chat_selector(self) -> dspy.Module:
        """Lazily initialized group chat selector."""
        self._ensure_modules_initialized()
        return self._group_chat_selector  # type: ignore[return-value]

    @group_chat_selector.setter
    def group_chat_selector(self, value: dspy.Module) -> None:
        """Allow setting group chat selector (for compiled module loading)."""
        self._group_chat_selector = value

    @property
    def nlu(self) -> DSPyNLU:
        """Lazily initialized NLU module."""
        self._ensure_modules_initialized()
        return self._nlu  # type: ignore[return-value]

    @nlu.setter
    def nlu(self, value: DSPyNLU) -> None:
        """Allow setting NLU module."""
        self._nlu = value

    def _robust_route(self, max_backtracks: int = 2, **kwargs) -> dspy.Prediction:
        """Execute routing with DSPy assertions."""
        # Call the router directly
        # We preserve the max_backtracks arg for interface compatibility
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

    def _get_predictor(self, module: dspy.Module) -> dspy.Module:
        """Extract the underlying Predict module from a ChainOfThought or similar wrapper."""
        if hasattr(module, "predictors"):
            preds = module.predictors()
            if preds:
                return preds[0]
        return module

    def predictors(self) -> list[dspy.Module]:
        """Return list of predictors for GEPA optimization.

        Note: GEPA expects ``predictors()`` to be callable; returning a
        list property breaks optimizer introspection.
        """
        preds = [
            self._get_predictor(self.analyzer),
            self._get_predictor(self.router),
            self._get_predictor(self.quality_assessor),
            self._get_predictor(self.progress_evaluator),
            self._get_predictor(self.tool_planner),
            # NOTE: self.judge removed in Plan #4 optimization
            self._get_predictor(self.simple_responder),
            self._get_predictor(self.group_chat_selector),
        ]
        if self.strategy_selector:
            preds.append(self._get_predictor(self.strategy_selector))
        return preds

    def named_predictors(self) -> list[tuple[str, dspy.Module]]:
        """Return predictor modules with stable names for GEPA."""

        preds = [
            ("analyzer", self._get_predictor(self.analyzer)),
            ("router", self._get_predictor(self.router)),
            ("quality_assessor", self._get_predictor(self.quality_assessor)),
            ("progress_evaluator", self._get_predictor(self.progress_evaluator)),
            ("tool_planner", self._get_predictor(self.tool_planner)),
            # NOTE: ("judge", ...) removed in Plan #4 optimization
            ("simple_responder", self._get_predictor(self.simple_responder)),
            ("group_chat_selector", self._get_predictor(self.group_chat_selector)),
        ]
        if self.strategy_selector:
            preds.append(("strategy_selector", self._get_predictor(self.strategy_selector)))
        return preds

    def set_tool_registry(self, tool_registry: Any) -> None:
        """Attach a tool registry to the supervisor."""
        self.tool_registry = tool_registry

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

            if not self.strategy_selector:
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

            prediction = self.strategy_selector(task=task, complexity_analysis=complexity_desc)

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
            intent_data = self.nlu.classify_intent(
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
            entities_data = self.nlu.extract_entities(
                task,
                entity_types=[
                    "Person",
                    "Organization",
                    "Location",
                    "Date",
                    "Time",
                    "Technology",
                    "Quantity",
                ],
            )

            prediction = self.analyzer(task=task)

            # Extract fields from prediction and align with AnalysisResult schema
            predicted_needs_web = getattr(prediction, "needs_web_search", None)
            time_sensitive = is_time_sensitive_task(task)
            needs_web_search = (
                bool(predicted_needs_web) if predicted_needs_web is not None else time_sensitive
            )

            capabilities = getattr(prediction, "required_capabilities", [])
            estimated_steps = getattr(prediction, "estimated_steps", 1)

            return {
                "complexity": getattr(prediction, "complexity", "medium"),
                "capabilities": capabilities,
                "required_capabilities": capabilities,
                "tool_requirements": getattr(prediction, "preferred_tools", []),
                "steps": estimated_steps,
                "estimated_steps": estimated_steps,
                "search_context": getattr(prediction, "search_context", ""),
                "needs_web_search": needs_web_search,
                "search_query": getattr(prediction, "search_query", ""),
                "urgency": getattr(prediction, "urgency", "medium"),
                "reasoning": getattr(prediction, "reasoning", ""),
                "time_sensitive": time_sensitive,
                "intent": intent_data,
                "entities": entities_data["entities"],
            }

    def route_task(
        self,
        task: str,
        team: dict[str, str],
        context: str = "",
        handoff_history: list[dict[str, Any]] | None = None,
        current_date: str | None = None,
        required_capabilities: list[str] | None = None,
        max_backtracks: int = 2,
    ) -> dict[str, Any]:
        """Route a task to the most appropriate agent(s).

        Args:
            task: The task to route
            team: Dictionary mapping agent names to their descriptions
            context: Optional context string
            handoff_history: Optional history of agent handoffs
            current_date: Optional current date string (YYYY-MM-DD)
            required_capabilities: Optional list of required capabilities to focus selection
            max_backtracks: Maximum number of DSPy assertion retries (default: 2)

        Returns:
            Dictionary containing routing decision (assigned_to, mode, subtasks)
        """
        with optional_span("DSPyReasoner.route_task", attributes={"task": task}):
            from datetime import datetime

            logger.info(f"Routing task: {task[:100]}...")

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

            # Format team description
            team_str = "\n".join([f"- {name}: {desc}" for name, desc in team.items()])

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

                tool_plan = getattr(prediction, "tool_plan", [])

                assigned_to = list(getattr(prediction, "assigned_to", []))
                execution_mode = getattr(prediction, "execution_mode", "delegated")
                subtasks = getattr(prediction, "subtasks", [task])

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

                reasoning_text = getattr(prediction, "reasoning", "")
                if reasoning_note:
                    reasoning_text = (reasoning_text + "\n" + reasoning_note).strip()

                return {
                    "task": task,
                    "assigned_to": assigned_to,
                    "mode": execution_mode,
                    "subtasks": subtasks,
                    "tool_plan": tool_plan,
                    "tool_requirements": tool_plan,  # Map for backward compatibility
                    "tool_goals": getattr(prediction, "tool_goals", ""),
                    "latency_budget": getattr(prediction, "latency_budget", "medium"),
                    "handoff_strategy": getattr(prediction, "handoff_strategy", ""),
                    "workflow_gates": getattr(prediction, "workflow_gates", ""),
                    "reasoning": reasoning_text,
                }

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
        with optional_span("DSPyReasoner.select_next_speaker"):
            logger.info("Selecting next speaker...")
            prediction = self.group_chat_selector(
                history=history, participants=participants, last_speaker=last_speaker
            )
            return {
                "next_speaker": getattr(prediction, "next_speaker", "TERMINATE"),
                "reasoning": getattr(prediction, "reasoning", ""),
            }

    def generate_simple_response(self, task: str) -> str:
        """Generate a direct response for a simple task.

        Args:
            task: The simple task or question

        Returns:
            The generated answer string
        """
        with optional_span("DSPyReasoner.generate_simple_response", attributes={"task": task}):
            logger.info(f"Generating direct response for simple task: {task[:100]}...")
            prediction = self.simple_responder(task=task)
            answer = getattr(prediction, "answer", "I could not generate a simple response.")
            logger.info(f"Generated answer: {answer[:100]}...")
            return answer

    def assess_quality(self, task: str = "", result: str = "", **kwargs: Any) -> dict[str, Any]:
        """Assess the quality of a task result.

        Args:
            task: The original task
            result: The result produced by the agent
            **kwargs: Compatibility arguments (requirements, results, etc.)

        Returns:
            Dictionary containing quality assessment (score, missing, improvements)
        """
        with optional_span("DSPyReasoner.assess_quality", attributes={"task": task}):
            actual_task = task or kwargs.get("requirements", "")
            actual_result = result or kwargs.get("results", "")

            logger.info("Assessing result quality...")
            prediction = self.quality_assessor(task=actual_task, result=actual_result)

            return {
                "score": getattr(prediction, "score", 0.0),
                "missing": getattr(prediction, "missing_elements", ""),
                "improvements": getattr(prediction, "required_improvements", ""),
                "reasoning": getattr(prediction, "reasoning", ""),
            }

    def evaluate_progress(self, task: str = "", result: str = "", **kwargs: Any) -> dict[str, Any]:
        """Evaluate progress and decide next steps (complete or refine).

        Args:
            task: The original task
            result: The current result
            **kwargs: Compatibility arguments (original_task, completed, etc.)

        Returns:
            Dictionary containing progress evaluation (action, feedback)
        """
        with optional_span("DSPyReasoner.evaluate_progress", attributes={"task": task}):
            # Handle parameter aliases from different executors
            actual_task = task or kwargs.get("original_task", "")
            actual_result = result or kwargs.get("completed", "")

            logger.info("Evaluating progress...")
            prediction = self.progress_evaluator(task=actual_task, result=actual_result)

            return {
                "action": getattr(prediction, "action", "complete"),
                "feedback": getattr(prediction, "feedback", ""),
                "reasoning": getattr(prediction, "reasoning", ""),
            }

    def decide_tools(
        self, task: str, team: dict[str, str], current_context: str = ""
    ) -> dict[str, Any]:
        """Decide which tools to use for a task (ReAct-style planning).

        Args:
            task: The task to execute
            team: Available agents/tools description
            current_context: Current execution context

        Returns:
            Dictionary containing tool plan
        """
        with optional_span("DSPyReasoner.decide_tools", attributes={"task": task}):
            logger.info("Deciding tools...")

            team_str = "\n".join([f"- {name}: {desc}" for name, desc in team.items()])

            prediction = self.tool_planner(task=task, available_tools=team_str)

            return {
                "tool_plan": getattr(prediction, "tool_plan", []),
                "reasoning": getattr(prediction, "reasoning", ""),
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
        """Return a summary of the execution history."""
        return {
            "history_count": len(self._execution_history),
            # Add more summary stats if needed
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
