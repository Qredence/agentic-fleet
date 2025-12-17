"""Module management for DSPyReasoner.

This module handles initialization and management of DSPy modules
for the DSPyReasoner class.
"""

from __future__ import annotations

import dspy

from ..utils.logger import setup_logger
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


# Module-level cache for DSPy module instances (stateless, can be shared)
_MODULE_CACHE: dict[str, dspy.Module] = {}


class ModuleManager:
    """Manages DSPy module initialization and caching."""

    def __init__(self, use_enhanced_signatures: bool = True, use_typed_signatures: bool = True):
        """Initialize module manager.

        Args:
            use_enhanced_signatures: Enable enhanced routing signatures
            use_typed_signatures: Use Pydantic-typed signatures
        """
        self.use_enhanced_signatures = use_enhanced_signatures
        self.use_typed_signatures = use_typed_signatures
        self._modules_initialized = False

        # Module placeholders
        self._analyzer: dspy.Module | None = None
        self._router: dspy.Module | None = None
        self._strategy_selector: dspy.Module | None = None
        self._quality_assessor: dspy.Module | None = None
        self._progress_evaluator: dspy.Module | None = None
        self._tool_planner: dspy.Module | None = None
        self._simple_responder: dspy.Module | None = None
        self._group_chat_selector: dspy.Module | None = None
        self._nlu: DSPyNLU | None = None
        self._event_narrator: dspy.Module | None = None

    def ensure_modules_initialized(self) -> None:
        """Lazily initialize DSPy modules on first use."""
        if self._modules_initialized:
            return

        # Initialize NLU
        if self._nlu is None:
            self._nlu = get_nlu_module()

        # Build cache key prefix based on configuration
        typed_suffix = "_typed" if self.use_typed_signatures else ""
        cache_key_prefix = (
            f"enhanced{typed_suffix}" if self.use_enhanced_signatures else f"standard{typed_suffix}"
        )

        # Initialize analyzer
        if self._analyzer is None:
            analyzer_key = f"{cache_key_prefix}_analyzer"
            if analyzer_key not in _MODULE_CACHE:
                if self.use_typed_signatures:
                    _MODULE_CACHE[analyzer_key] = dspy.ChainOfThought(TypedTaskAnalysis)
                else:
                    _MODULE_CACHE[analyzer_key] = dspy.ChainOfThought(TaskAnalysis)
            self._analyzer = _MODULE_CACHE[analyzer_key]

        # Initialize router and strategy selector
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

        # Initialize quality assessor
        if self._quality_assessor is None:
            qa_key = f"quality_assessor{typed_suffix}"
            if qa_key not in _MODULE_CACHE:
                if self.use_typed_signatures:
                    _MODULE_CACHE[qa_key] = dspy.ChainOfThought(TypedQualityAssessment)
                else:
                    _MODULE_CACHE[qa_key] = dspy.ChainOfThought(QualityAssessment)
            self._quality_assessor = _MODULE_CACHE[qa_key]

        # Initialize progress evaluator
        if self._progress_evaluator is None:
            pe_key = f"progress_evaluator{typed_suffix}"
            if pe_key not in _MODULE_CACHE:
                if self.use_typed_signatures:
                    _MODULE_CACHE[pe_key] = dspy.ChainOfThought(TypedProgressEvaluation)
                else:
                    _MODULE_CACHE[pe_key] = dspy.ChainOfThought(ProgressEvaluation)
            self._progress_evaluator = _MODULE_CACHE[pe_key]

        # Initialize tool planner
        if self._tool_planner is None:
            tp_key = f"tool_planner{typed_suffix}"
            if tp_key not in _MODULE_CACHE:
                if self.use_typed_signatures:
                    _MODULE_CACHE[tp_key] = dspy.ChainOfThought(TypedToolPlan)
                else:
                    _MODULE_CACHE[tp_key] = dspy.ChainOfThought(ToolPlan)
            self._tool_planner = _MODULE_CACHE[tp_key]

        # Initialize simple responder
        if self._simple_responder is None:
            sr_key = "simple_responder"
            if sr_key not in _MODULE_CACHE:
                _MODULE_CACHE[sr_key] = dspy.Predict(SimpleResponse)
            self._simple_responder = _MODULE_CACHE[sr_key]

        # Initialize group chat selector
        if self._group_chat_selector is None:
            gc_key = "group_chat_selector"
            if gc_key not in _MODULE_CACHE:
                _MODULE_CACHE[gc_key] = dspy.ChainOfThought(GroupChatSpeakerSelection)
            self._group_chat_selector = _MODULE_CACHE[gc_key]

        # Initialize event narrator
        if self._event_narrator is None:
            en_key = "event_narrator"
            if en_key not in _MODULE_CACHE:
                from ..workflows.narrator import EventNarrator

                _MODULE_CACHE[en_key] = EventNarrator()
            self._event_narrator = _MODULE_CACHE[en_key]

        self._modules_initialized = True
        mode_str = "typed" if self.use_typed_signatures else "standard"
        logger.debug(f"DSPy modules initialized (lazy, mode={mode_str})")

    def get_predictors(self) -> list[dspy.Module]:
        """Get all DSPy predictors for compilation."""
        self.ensure_modules_initialized()
        predictors = []

        if self._analyzer:
            predictors.append(self._analyzer)
        if self._router:
            predictors.append(self._router)
        if self._strategy_selector:
            predictors.append(self._strategy_selector)
        if self._quality_assessor:
            predictors.append(self._quality_assessor)
        if self._progress_evaluator:
            predictors.append(self._progress_evaluator)
        if self._tool_planner:
            predictors.append(self._tool_planner)
        if self._simple_responder:
            predictors.append(self._simple_responder)
        if self._group_chat_selector:
            predictors.append(self._group_chat_selector)

        return predictors

    def get_named_predictors(self) -> list[tuple[str, dspy.Module]]:
        """Get all DSPy predictors with names."""
        self.ensure_modules_initialized()
        predictors = []

        if self._analyzer:
            predictors.append(("analyzer", self._analyzer))
        if self._router:
            predictors.append(("router", self._router))
        if self._strategy_selector:
            predictors.append(("strategy_selector", self._strategy_selector))
        if self._quality_assessor:
            predictors.append(("quality_assessor", self._quality_assessor))
        if self._progress_evaluator:
            predictors.append(("progress_evaluator", self._progress_evaluator))
        if self._tool_planner:
            predictors.append(("tool_planner", self._tool_planner))
        if self._simple_responder:
            predictors.append(("simple_responder", self._simple_responder))
        if self._group_chat_selector:
            predictors.append(("group_chat_selector", self._group_chat_selector))

        return predictors

    def clear_cache(self) -> None:
        """Clear module cache."""
        global _MODULE_CACHE
        _MODULE_CACHE.clear()
        self._modules_initialized = False

        # Reset module references
        self._analyzer = None
        self._router = None
        self._strategy_selector = None
        self._quality_assessor = None
        self._progress_evaluator = None
        self._tool_planner = None
        self._simple_responder = None
        self._group_chat_selector = None
        self._nlu = None
        self._event_narrator = None

        logger.debug("Cleared DSPy module cache")

    # Property getters for modules
    @property
    def analyzer(self) -> dspy.Module:
        """Return the analyzer module."""
        self.ensure_modules_initialized()
        return self._analyzer  # type: ignore[return-value]

    @analyzer.setter
    def analyzer(self, value: dspy.Module) -> None:
        self._analyzer = value

    @property
    def router(self) -> dspy.Module:
        """Return the router module."""
        self.ensure_modules_initialized()
        return self._router  # type: ignore[return-value]

    @router.setter
    def router(self, value: dspy.Module) -> None:
        self._router = value

    @property
    def strategy_selector(self) -> dspy.Module | None:
        """Return the strategy selector module (if enabled)."""
        self.ensure_modules_initialized()
        return self._strategy_selector

    @strategy_selector.setter
    def strategy_selector(self, value: dspy.Module | None) -> None:
        self._strategy_selector = value

    @property
    def quality_assessor(self) -> dspy.Module:
        """Return the quality assessor module."""
        self.ensure_modules_initialized()
        return self._quality_assessor  # type: ignore[return-value]

    @quality_assessor.setter
    def quality_assessor(self, value: dspy.Module) -> None:
        self._quality_assessor = value

    @property
    def progress_evaluator(self) -> dspy.Module:
        """Return the progress evaluator module."""
        self.ensure_modules_initialized()
        return self._progress_evaluator  # type: ignore[return-value]

    @progress_evaluator.setter
    def progress_evaluator(self, value: dspy.Module) -> None:
        self._progress_evaluator = value

    @property
    def tool_planner(self) -> dspy.Module:
        """Return the tool planner module."""
        self.ensure_modules_initialized()
        return self._tool_planner  # type: ignore[return-value]

    @tool_planner.setter
    def tool_planner(self, value: dspy.Module) -> None:
        self._tool_planner = value

    @property
    def simple_responder(self) -> dspy.Module:
        """Return the simple responder module."""
        self.ensure_modules_initialized()
        return self._simple_responder  # type: ignore[return-value]

    @simple_responder.setter
    def simple_responder(self, value: dspy.Module) -> None:
        self._simple_responder = value

    @property
    def group_chat_selector(self) -> dspy.Module:
        """Return the group chat selector module."""
        self.ensure_modules_initialized()
        return self._group_chat_selector  # type: ignore[return-value]

    @group_chat_selector.setter
    def group_chat_selector(self, value: dspy.Module) -> None:
        self._group_chat_selector = value

    @property
    def nlu(self) -> DSPyNLU:
        """Return the NLU module."""
        self.ensure_modules_initialized()
        return self._nlu  # type: ignore[return-value]

    @nlu.setter
    def nlu(self, value: DSPyNLU) -> None:
        self._nlu = value

    @property
    def event_narrator(self) -> dspy.Module:
        """Return the event narrator module."""
        self.ensure_modules_initialized()
        return self._event_narrator  # type: ignore[return-value]

    @event_narrator.setter
    def event_narrator(self, value: dspy.Module) -> None:
        self._event_narrator = value
