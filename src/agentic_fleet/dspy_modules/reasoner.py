"""DSPy-powered reasoner for intelligent orchestration.

This module implements the DSPyReasoner, which uses DSPy's language model
programming capabilities to perform high-level cognitive tasks:
- Task Analysis: Decomposing complex requests
- Routing: Assigning tasks to the best agents
- Quality Assessment: Evaluating results against criteria
- Progress Tracking: Monitoring execution state
- Tool Planning: Deciding which tools to use

DSPy 3.x Note:
When `use_typed_signatures=True`, the reasoner uses Pydantic-based typed
signatures for structured outputs. This provides:
- Better output parsing reliability
- Automatic validation and type coercion
- Clear error messages on parse failures
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Any

import dspy

from agentic_fleet.utils.cfg import load_config

from ..utils.logger import setup_logger
from ..utils.telemetry import optional_span
from ..workflows.exceptions import ToolError
from .nlu import DSPyNLU, get_nlu_module
from .reasoner_utils import get_reasoner_source_hash, is_simple_task, is_time_sensitive_task
from .signatures import (
    EnhancedTaskRouting,
    GroupChatSpeakerSelection,
    ProgressEvaluation,
    QualityAssessment,
    SimpleResponse,
    TaskAnalysis,
    TaskRouting,
    ToolPlan,
    # Typed signatures (DSPy 3.x with Pydantic)
    TypedEnhancedRouting,
    TypedProgressEvaluation,
    TypedQualityAssessment,
    TypedTaskAnalysis,
    TypedToolPlan,
    TypedWorkflowStrategy,
    WorkflowStrategy,
)

logger = setup_logger(__name__)


def _find_upwards(start: Path, marker: str) -> Path | None:
    """Search upward from start for a file or directory named marker. Return the containing directory, or None."""
    current = start
    while True:
        candidate = current / marker
        if candidate.exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


def _search_bases() -> list[Path]:
    resolved = Path(__file__).resolve()
    # Find repo root by searching for pyproject.toml
    repo_root = _find_upwards(resolved.parent, "pyproject.toml")
    if repo_root is None:
        repo_root = resolved.parents[-1]
    # Find package root by searching for the topmost __init__.py
    package_root = None
    current = resolved.parent
    last_with_init = None
    while True:
        if (current / "__init__.py").exists():
            last_with_init = current
        else:
            break
        if current.parent == current:
            break
        current = current.parent
    package_root = last_with_init if last_with_init is not None else resolved.parents[-1]
    module_dir = resolved.parent
    return [repo_root, package_root, module_dir, Path.cwd()]


@lru_cache(maxsize=1)
def _resolve_compiled_reasoner_path() -> Path:
    config: dict[str, Any] = {}
    try:
        config = load_config(validate=False)
    except Exception as exc:  # pragma: no cover - best-effort fallback
        logger.debug("Failed to load workflow config for compiled reasoner path: %s", exc)

    dspy_config = config.get("dspy", {})
    relative_path = Path(
        dspy_config.get("compiled_reasoner_path", ".var/cache/dspy/compiled_reasoner.json")
    ).expanduser()
    if relative_path.is_absolute():
        return relative_path

    bases = _search_bases()
    for base in bases:
        candidate = (base / relative_path).resolve()
        if candidate.exists():
            return candidate

    return (bases[0] / relative_path).resolve()


def get_configured_compiled_reasoner_path() -> Path:
    """Return the configured path to the compiled DSPy reasoner artifact."""

    return _resolve_compiled_reasoner_path()


# Module-level cache for DSPy module instances (stateless, can be shared)
_MODULE_CACHE: dict[str, dspy.Module] = {}


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
            use_typed_signatures (bool): Use Pydantic-typed signatures for structured/typed module outputs.
            enable_routing_cache (bool): Enable in-memory caching of routing decisions to reduce repeated model calls.
            cache_ttl_seconds (int): Time-to-live for cached routing entries in seconds.
            cache_max_entries (int): Maximum number of cached routing entries to retain in memory.
        """
        super().__init__()
        self.use_enhanced_signatures = use_enhanced_signatures
        self.use_typed_signatures = use_typed_signatures
        self.enable_routing_cache = enable_routing_cache
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache_max_entries = max(1, int(cache_max_entries))

        self._execution_history: list[dict[str, Any]] = []
        self._modules_initialized = False
        self.tool_registry: Any | None = None

        # Routing cache for performance optimization (OrderedDict for O(1) LRU eviction)
        self._routing_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()

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
        """
        Lazily initialize DSPy modules and related runtime defaults on first use.

        Ensures module placeholders and backward-compatible defaults (execution history,
        typed-signature flag, routing cache settings and TTL) exist, then initializes any
        DSPy modules that have not been manually provided. Honors the instance's
        use_enhanced_signatures and use_typed_signatures configuration when selecting
        which signature variants to create. After this returns, the reasoner has all
        predictor/chain placeholders populated or left as explicitly overridden for testing.
        """
        # Backward compatibility: compiled supervisors pickled before these fields
        # existed won't have them set on load.
        if not hasattr(self, "_modules_initialized"):
            self._modules_initialized = False
        if not hasattr(self, "_execution_history"):
            self._execution_history = []
        if not hasattr(self, "use_typed_signatures"):
            self.use_typed_signatures = False
        if not hasattr(self, "enable_routing_cache"):
            self.enable_routing_cache = True
        if not hasattr(self, "cache_ttl_seconds"):
            self.cache_ttl_seconds = 300
        if not hasattr(self, "_routing_cache"):
            self._routing_cache = OrderedDict()
        if not hasattr(self, "cache_max_entries"):
            self.cache_max_entries = 1024

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
            "_event_narrator",
        ):
            if not hasattr(self, attr):
                setattr(self, attr, None)

        if self._modules_initialized:
            return

        global _MODULE_CACHE

        # Build cache key prefix based on configuration
        typed_suffix = "_typed" if self.use_typed_signatures else ""
        cache_key_prefix = (
            f"enhanced{typed_suffix}" if self.use_enhanced_signatures else f"standard{typed_suffix}"
        )

        # Only initialize if not already set (allows mocking in tests)
        # NLU
        if self._nlu is None:
            self._nlu = get_nlu_module()

        # Analyzer - use typed signature if enabled
        if self._analyzer is None:
            analyzer_key = f"{cache_key_prefix}_analyzer"
            if analyzer_key not in _MODULE_CACHE:
                if self.use_typed_signatures:
                    _MODULE_CACHE[analyzer_key] = dspy.ChainOfThought(TypedTaskAnalysis)
                else:
                    _MODULE_CACHE[analyzer_key] = dspy.ChainOfThought(TaskAnalysis)
            self._analyzer = _MODULE_CACHE[analyzer_key]

        # Router and strategy selector - use typed signatures if enabled
        if self._router is None:
            if self.use_enhanced_signatures:
                router_key = f"{cache_key_prefix}_router"
                if router_key not in _MODULE_CACHE:
                    if self.use_typed_signatures:
                        _MODULE_CACHE[router_key] = dspy.Predict(TypedEnhancedRouting)
                    else:
                        _MODULE_CACHE[router_key] = dspy.Predict(EnhancedTaskRouting)
                self._router = _MODULE_CACHE[router_key]

                if self._strategy_selector is None:
                    strategy_key = f"{cache_key_prefix}_strategy"
                    if strategy_key not in _MODULE_CACHE:
                        if self.use_typed_signatures:
                            _MODULE_CACHE[strategy_key] = dspy.ChainOfThought(TypedWorkflowStrategy)
                        else:
                            _MODULE_CACHE[strategy_key] = dspy.ChainOfThought(WorkflowStrategy)
                    self._strategy_selector = _MODULE_CACHE[strategy_key]
            else:
                router_key = f"{cache_key_prefix}_router"
                if router_key not in _MODULE_CACHE:
                    _MODULE_CACHE[router_key] = dspy.Predict(TaskRouting)
                self._router = _MODULE_CACHE[router_key]

        # Quality assessor - use typed signature if enabled
        if self._quality_assessor is None:
            qa_key = f"quality_assessor{typed_suffix}"
            if qa_key not in _MODULE_CACHE:
                if self.use_typed_signatures:
                    _MODULE_CACHE[qa_key] = dspy.ChainOfThought(TypedQualityAssessment)
                else:
                    _MODULE_CACHE[qa_key] = dspy.ChainOfThought(QualityAssessment)
            self._quality_assessor = _MODULE_CACHE[qa_key]

        # Progress evaluator - use typed signature if enabled
        if self._progress_evaluator is None:
            pe_key = f"progress_evaluator{typed_suffix}"
            if pe_key not in _MODULE_CACHE:
                if self.use_typed_signatures:
                    _MODULE_CACHE[pe_key] = dspy.ChainOfThought(TypedProgressEvaluation)
                else:
                    _MODULE_CACHE[pe_key] = dspy.ChainOfThought(ProgressEvaluation)
            self._progress_evaluator = _MODULE_CACHE[pe_key]

        # Tool planner - use typed signature if enabled
        if self._tool_planner is None:
            tp_key = f"tool_planner{typed_suffix}"
            if tp_key not in _MODULE_CACHE:
                if self.use_typed_signatures:
                    _MODULE_CACHE[tp_key] = dspy.ChainOfThought(TypedToolPlan)
                else:
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

        # Event Narrator
        if self._event_narrator is None:
            en_key = "event_narrator"
            if en_key not in _MODULE_CACHE:
                from agentic_fleet.workflows.narrator import EventNarrator

                _MODULE_CACHE[en_key] = EventNarrator()
            self._event_narrator = _MODULE_CACHE[en_key]

        self._modules_initialized = True
        mode_str = "typed" if self.use_typed_signatures else "standard"
        logger.debug(f"DSPy modules initialized (lazy, mode={mode_str})")

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
        return self._event_narrator  # type: ignore[return-value]

    @event_narrator.setter
    def event_narrator(self, value: dspy.Module) -> None:
        """Allow setting event narrator."""
        self._event_narrator = value

    def narrate_events(self, events: list[dict[str, Any]]) -> str:
        """Generate a narrative summary from workflow events.

        Args:
            events: List of event dictionaries.

        Returns:
            Narrative string.
        """
        with optional_span("DSPyReasoner.narrate_events"):
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
        """
        Provide lazy access to the task analyzer module.

        Returns:
            dspy.Module: The analyzer module used for task analysis; initialized on first access.
        """
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
            self._router = routing_module
            logger.debug("Injected external routing decision module")
        if quality_module is not None:
            self._quality_assessor = quality_module
            logger.debug("Injected external quality assessment module")
        if tool_planning_module is not None:
            self._tool_planner = tool_planning_module
            logger.debug("Injected external tool planning module")

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
        with optional_span("DSPyReasoner.route_task", attributes={"task": task}):
            from datetime import datetime

            logger.info(f"Routing task: {task[:100]}...")

            # Check cache first (unless skipped or simple task)
            if not skip_cache and self.enable_routing_cache:
                team_key = str(sorted(team.keys()))
                cache_key = self._get_cache_key(task, team_key)
                cached_result = self._get_cached_routing(cache_key)
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
                    team_key = str(sorted(team.keys()))
                    cache_key = self._get_cache_key(task, team_key)
                    self._cache_routing(cache_key, result)

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
        """
        Provide a brief summary of the reasoner's execution state.

        Returns:
            summary (dict): A dictionary with keys:
                history_count (int): Number of recorded execution events.
                routing_cache_size (int): Number of entries currently stored in the routing cache.
                use_typed_signatures (bool): Whether typed (Pydantic) signatures are enabled.
        """
        return {
            "history_count": len(self._execution_history),
            "routing_cache_size": len(self._routing_cache),
            "use_typed_signatures": self.use_typed_signatures,
        }

    # --- Cache management ---

    def _get_cache_key(self, task: str, team_key: str) -> str:
        """
        Create a stable 16-hex-character cache key derived from `task` and `team_key`.

        Parameters:
            task (str): The task description used to derive the key.
            team_key (str): String representing the team configuration or capabilities.

        Returns:
            cache_key (str): 16-character hex MD5 digest of the combined `task` and `team_key`.
        """
        combined = f"{task}|{team_key}"
        # MD5 used for cache key generation, not security
        return hashlib.md5(combined.encode(), usedforsecurity=False).hexdigest()[:16]

    def _get_cached_routing(self, cache_key: str) -> dict[str, Any] | None:
        """
        Return a previously stored routing decision for `cache_key` if routing cache is enabled and the entry exists and is not expired.

        Parameters:
            cache_key (str): Key identifying the cached routing decision.

        Returns:
            dict[str, Any] | None: The cached routing decision if present and fresh; `None` if caching is disabled, the key is absent, or the entry has expired.
        """
        if not self.enable_routing_cache:
            return None

        if cache_key not in self._routing_cache:
            return None

        cached = self._routing_cache[cache_key]
        if time.time() - cached["timestamp"] > self.cache_ttl_seconds:
            # Expired - remove from cache
            del self._routing_cache[cache_key]
            return None

        # Move to end to maintain LRU order (mark as most recently used)
        self._routing_cache.move_to_end(cache_key)
        logger.debug(f"Cache hit for routing key {cache_key[:8]}...")
        return cached["result"]

    def _cache_routing(self, cache_key: str, result: dict[str, Any]) -> None:
        """
        Store a routing decision in the routing cache with a timestamp.

        If routing cache is disabled, this is a no-op.

        Parameters:
            cache_key (str): Key under which to store the routing decision.
            result (dict[str, Any]): Routing decision data to cache.
        """
        if not self.enable_routing_cache:
            return

        # Bound memory usage: evict oldest entries when exceeding the cap.
        # OrderedDict maintains insertion order, enabling O(1) eviction of the oldest entry.
        if len(self._routing_cache) >= self.cache_max_entries:
            try:
                # Remove the oldest entry (first item in OrderedDict)
                self._routing_cache.popitem(last=False)
            except Exception:
                # If eviction fails for any reason, fall back to clearing to avoid unbounded growth.
                self._routing_cache.clear()

        # Store the new entry (OrderedDict automatically places it at the end)
        self._routing_cache[cache_key] = {
            "result": result,
            "timestamp": time.time(),
        }

    def clear_routing_cache(self) -> None:
        """Clear the routing cache."""
        self._routing_cache.clear()
        logger.debug("Routing cache cleared")

    def _extract_typed_routing_decision(self, prediction: Any) -> dict[str, Any]:
        """
        Extract a plain dict of routing decision fields from a DSPy prediction that may use typed (Pydantic) signatures.

        If the prediction contains a typed `decision` (Pydantic model), this function returns that model serialized to a dict (supports Pydantic v2 `model_dump()` and v1 `dict()`), or falls back to reading common decision attributes. If there is no typed `decision`, the function extracts routing fields directly from the top-level prediction object.

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
        # Check if we have a typed 'decision' field (Pydantic model)
        decision = getattr(prediction, "decision", None)
        if decision is not None:
            # It's a Pydantic model - extract fields
            if hasattr(decision, "model_dump"):
                return decision.model_dump()
            elif hasattr(decision, "dict"):
                return decision.dict()
            else:
                # Fallback: try to get attributes
                return {
                    "assigned_to": getattr(decision, "assigned_to", []),
                    "execution_mode": getattr(decision, "execution_mode", "delegated"),
                    "subtasks": getattr(decision, "subtasks", []),
                    "tool_requirements": getattr(decision, "tool_requirements", []),
                    "tool_plan": getattr(decision, "tool_plan", []),
                    "tool_goals": getattr(decision, "tool_goals", ""),
                    "latency_budget": getattr(decision, "latency_budget", "medium"),
                    "handoff_strategy": getattr(decision, "handoff_strategy", ""),
                    "workflow_gates": getattr(decision, "workflow_gates", ""),
                    "reasoning": getattr(decision, "reasoning", ""),
                }

        # Not a typed signature - extract fields directly from prediction
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
