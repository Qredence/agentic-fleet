"""Tests for DSPyReasoner and its cognitive functions.

These tests mock DSPy modules to avoid actual LLM calls while verifying
the reasoner's routing logic, fallback behavior, and response parsing.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from agentic_fleet.dspy_modules.reasoner import DSPyReasoner


class MockPrediction:
    """Mock DSPy prediction object with configurable attributes."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


@pytest.fixture
def mock_dspy_lm():
    """Mock DSPy language model to avoid LLM calls."""
    with patch("dspy.settings.configure") as mock_config:
        mock_lm = MagicMock()
        mock_config.return_value = None
        yield mock_lm


@pytest.fixture
def reasoner():
    """Create a DSPyReasoner instance with mocked modules."""
    r = DSPyReasoner(use_enhanced_signatures=False)
    return r


@pytest.fixture
def enhanced_reasoner():
    """Create a DSPyReasoner instance with enhanced signatures."""
    r = DSPyReasoner(use_enhanced_signatures=True)
    return r


class TestDSPyReasonerInit:
    """Tests for DSPyReasoner initialization."""

    def test_initializes_with_default_settings(self, reasoner):
        """Verify default initialization creates expected modules."""
        assert reasoner.use_enhanced_signatures is False
        assert reasoner.analyzer is not None
        assert reasoner.router is not None
        assert reasoner.quality_assessor is not None
        assert reasoner.progress_evaluator is not None
        assert reasoner.tool_planner is not None
        assert reasoner.simple_responder is not None
        assert reasoner.tool_registry is None
        assert reasoner._execution_history == []

    def test_initializes_with_enhanced_signatures(self, enhanced_reasoner):
        """Verify enhanced signatures creates strategy selector."""
        assert enhanced_reasoner.use_enhanced_signatures is True
        assert enhanced_reasoner.strategy_selector is not None

    def test_set_tool_registry(self, reasoner):
        """Verify tool registry can be attached."""
        mock_registry = MagicMock()
        reasoner.set_tool_registry(mock_registry)
        assert reasoner.tool_registry is mock_registry


class TestDSPyReasonerAnalyzeTask:
    """Tests for analyze_task method."""

    def test_analyze_task_returns_expected_structure(self, reasoner):
        """Verify analyze_task returns dictionary with required keys."""
        # Mock the analyzer module
        reasoner.analyzer = MagicMock(
            return_value=MockPrediction(
                complexity="medium",
                required_capabilities=["research", "writing"],
                estimated_steps=3,
                reasoning="Task requires research and synthesis",
            )
        )

        result = reasoner.analyze_task("Research quantum computing trends")

        assert "complexity" in result
        assert "required_capabilities" in result
        assert "estimated_steps" in result
        assert "reasoning" in result
        assert "time_sensitive" in result
        assert "needs_web_search" in result

    def test_analyze_task_handles_missing_attributes(self, reasoner):
        """Verify graceful handling when prediction lacks attributes."""
        reasoner.analyzer = MagicMock(return_value=MockPrediction())

        result = reasoner.analyze_task("Test task")

        assert result["complexity"] == "medium"  # Default
        assert result["required_capabilities"] == []  # Default
        assert result["estimated_steps"] == 1  # Default


class TestDSPyReasonerRouteTask:
    """Tests for route_task method."""

    def test_route_task_simple_task_to_writer(self, reasoner):
        """Verify simple tasks are routed directly to Writer."""
        team = {"Writer": "Writing and composition agent"}

        result = reasoner.route_task("Hello", team=team, context="")

        assert result["assigned_to"] == ["Writer"]
        assert result["mode"] == "delegated"
        assert "Simple/heartbeat" in result["reasoning"]

    def test_route_task_falls_back_when_no_writer(self, reasoner):
        """Verify fallback routing when Writer not in team."""
        # Mock the router to return a prediction
        reasoner.router = MagicMock(
            return_value=MockPrediction(
                assigned_to=["Researcher"],
                mode="delegated",
                subtasks=["Research the topic"],
                tool_requirements=["web_search"],
                reasoning="Fallback routing",
            )
        )

        team = {"Researcher": "Research agent"}
        result = reasoner.route_task("Hello", team=team, context="")

        # Should have called the router since Writer not available
        assert "Researcher" in result["assigned_to"]

    def test_route_task_includes_tool_requirements(self, reasoner):
        """Verify tool requirements are included in routing result."""
        reasoner.router = MagicMock(
            return_value=MockPrediction(
                assigned_to=["Analyst"],
                mode="delegated",
                subtasks=["Analyze data"],
                tool_requirements=["code_interpreter"],
                reasoning="Analysis task",
            )
        )

        team = {"Analyst": "Data analysis agent"}
        result = reasoner.route_task("Analyze this dataset", team=team)

        assert "tool_requirements" in result

    def test_route_task_with_current_date(self, reasoner):
        """Verify current_date is used when provided."""
        reasoner.router = MagicMock(
            return_value=MockPrediction(
                assigned_to=["Researcher"],
                mode="delegated",
                subtasks=["Research"],
                tool_requirements=[],
                reasoning="Date-aware routing",
            )
        )

        team = {"Researcher": "Research agent"}
        result = reasoner.route_task("What happened today?", team=team, current_date="2025-11-25")

        assert result is not None


class TestDSPyReasonerEnhancedRouting:
    """Tests for enhanced routing with time-sensitive tasks."""

    def test_time_sensitive_task_adds_tavily(self, enhanced_reasoner):
        """Verify time-sensitive tasks get Tavily tool added."""
        # Mock the router and tool registry
        enhanced_reasoner.router = MagicMock(
            return_value=MockPrediction(
                assigned_to=["Writer"],
                execution_mode="delegated",
                subtasks=["Write about news"],
                tool_plan=[],
                tool_goals="",
                latency_budget="medium",
                handoff_strategy="",
                workflow_gates="",
                reasoning="Standard routing",
            )
        )

        # Mock tool registry with Tavily
        mock_registry = MagicMock()
        mock_registry.get_tool_descriptions.return_value = "TavilySearchTool: Web search"
        mock_registry.get_tool_by_name.return_value = MagicMock(name="TavilySearchTool")
        enhanced_reasoner.tool_registry = mock_registry

        team = {"Writer": "Writing agent", "Researcher": "Research agent"}

        # Task with year in it (time-sensitive)
        result = enhanced_reasoner.route_task("What happened in November 2025?", team=team)

        # Should add Researcher and Tavily for time-sensitive tasks
        assert "Researcher" in result["assigned_to"]
        assert "Tavily" in result.get("reasoning", "") or len(result.get("tool_plan", [])) > 0


class TestDSPyReasonerQualityAssessment:
    """Tests for assess_quality method."""

    def test_assess_quality_returns_structure(self, reasoner):
        """Verify assess_quality returns expected dictionary structure."""
        reasoner.quality_assessor = MagicMock(
            return_value=MockPrediction(
                score=8.5,
                missing_elements="None",
                required_improvements="None",
                reasoning="Good quality response",
            )
        )

        result = reasoner.assess_quality(task="Write a poem", result="Roses are red...")

        assert "score" in result
        assert "missing" in result
        assert "improvements" in result
        assert "reasoning" in result
        assert result["score"] == 8.5

    def test_assess_quality_handles_kwargs_aliases(self, reasoner):
        """Verify backward-compatible kwargs (requirements, results) work."""
        reasoner.quality_assessor = MagicMock(
            return_value=MockPrediction(
                score=7.0,
                missing_elements="Citations",
                required_improvements="Add sources",
                reasoning="Missing citations",
            )
        )

        # Use legacy parameter names
        result = reasoner.assess_quality(requirements="Research topic", results="Some findings")

        reasoner.quality_assessor.assert_called_once()
        assert result["score"] == 7.0


class TestDSPyReasonerProgressEvaluation:
    """Tests for evaluate_progress method."""

    def test_evaluate_progress_returns_structure(self, reasoner):
        """Verify evaluate_progress returns expected dictionary structure."""
        reasoner.progress_evaluator = MagicMock(
            return_value=MockPrediction(
                action="complete",
                feedback="Task fully addressed",
                reasoning="All requirements met",
            )
        )

        result = reasoner.evaluate_progress(task="Write report", result="Report content...")

        assert "action" in result
        assert "feedback" in result
        assert "reasoning" in result
        assert result["action"] == "complete"

    def test_evaluate_progress_refine_action(self, reasoner):
        """Verify refine action is returned when needed."""
        reasoner.progress_evaluator = MagicMock(
            return_value=MockPrediction(
                action="refine",
                feedback="Need more detail",
                reasoning="Response incomplete",
            )
        )

        result = reasoner.evaluate_progress(task="Detailed analysis", result="Brief summary")

        assert result["action"] == "refine"


class TestDSPyReasonerToolPlanning:
    """Tests for decide_tools method."""

    def test_decide_tools_returns_tool_plan(self, reasoner):
        """Verify decide_tools returns tool plan structure."""
        reasoner.tool_planner = MagicMock(
            return_value=MockPrediction(
                tool_plan=["web_search", "code_interpreter"],
                reasoning="Need search and code execution",
            )
        )

        team = {"Researcher": "Research agent", "Analyst": "Data analyst"}
        result = reasoner.decide_tools("Analyze web data", team=team)

        assert "tool_plan" in result
        assert "reasoning" in result
        assert len(result["tool_plan"]) == 2


class TestDSPyReasonerSimpleResponse:
    """Tests for generate_simple_response method."""

    def test_generate_simple_response(self, reasoner):
        """Verify simple response generation."""
        reasoner.simple_responder = MagicMock(
            return_value=MockPrediction(answer="Hello! How can I help you?")
        )

        result = reasoner.generate_simple_response("Hello")

        assert result == "Hello! How can I help you?"

    def test_generate_simple_response_fallback(self, reasoner):
        """Verify fallback when answer attribute missing."""
        reasoner.simple_responder = MagicMock(return_value=MockPrediction())

        result = reasoner.generate_simple_response("Test")

        assert "could not generate" in result.lower()


class TestDSPyReasonerWorkflowMode:
    """Tests for select_workflow_mode method."""

    def test_fast_path_for_simple_task(self, enhanced_reasoner):
        """Verify fast_path is selected for trivial tasks."""
        result = enhanced_reasoner.select_workflow_mode("hello")

        assert result["mode"] == "fast_path"
        assert "trivial" in result["reasoning"].lower()

    def test_standard_mode_without_strategy_selector(self, reasoner):
        """Verify standard mode when strategy_selector is None."""
        result = reasoner.select_workflow_mode("Complex multi-step task")

        # Without enhanced signatures, strategy_selector is None
        # Falls back to standard mode
        assert result["mode"] in ["standard", "fast_path"]

    def test_workflow_mode_with_strategy_selector(self, enhanced_reasoner):
        """Verify strategy selector is called for complex tasks."""
        enhanced_reasoner.strategy_selector = MagicMock(
            return_value=MockPrediction(
                workflow_mode="handoff",
                reasoning="Task requires multiple handoffs",
            )
        )

        # Mock analyzer to avoid actual DSPy calls
        enhanced_reasoner.analyzer = MagicMock(
            return_value=MockPrediction(
                complexity="high",
                required_capabilities=["research", "analysis"],
                estimated_steps=5,
                reasoning="Complex task",
            )
        )

        result = enhanced_reasoner.select_workflow_mode("Write a comprehensive research paper")

        assert result["mode"] == "handoff"


class TestDSPyReasonerPredictors:
    """Tests for predictor introspection methods."""

    def test_predictors_returns_list(self, reasoner):
        """Verify predictors() returns a list of modules."""
        preds = reasoner.predictors()

        assert isinstance(preds, list)
        assert len(preds) >= 7  # At least 7 core predictors

    def test_named_predictors_returns_tuples(self, reasoner):
        """Verify named_predictors() returns name-module tuples."""
        named = reasoner.named_predictors()

        assert isinstance(named, list)
        assert all(isinstance(item, tuple) and len(item) == 2 for item in named)
        names = [name for name, _ in named]
        assert "analyzer" in names
        assert "router" in names
        assert "quality_assessor" in names

    def test_enhanced_reasoner_includes_strategy_selector(self, enhanced_reasoner):
        """Verify enhanced reasoner includes strategy_selector in predictors."""
        named = enhanced_reasoner.named_predictors()

        names = [name for name, _ in named]
        assert "strategy_selector" in names


class TestDSPyReasonerForward:
    """Tests for the forward() method used in DSPy optimization."""

    def test_forward_calls_router(self, reasoner):
        """Verify forward() delegates to _robust_route."""
        reasoner.router = MagicMock(
            return_value=MockPrediction(
                assigned_to=["Writer"],
                mode="delegated",
                subtasks=["Write"],
            )
        )

        result = reasoner.forward(
            task="Write something",
            team="Writer: Writing agent",
            context="",
        )

        reasoner.router.assert_called_once()
        assert result is not None

    def test_forward_handles_field_aliases(self, enhanced_reasoner):
        """Verify forward handles team_capabilities and current_context aliases."""
        enhanced_reasoner.router = MagicMock(
            return_value=MockPrediction(
                assigned_to=["Researcher"],
                execution_mode="delegated",
                subtasks=["Research"],
            )
        )

        result = enhanced_reasoner.forward(
            task="Research topic",
            team_capabilities="Researcher: Research agent",
            current_context="Prior context",
        )

        enhanced_reasoner.router.assert_called_once()
        assert result is not None


class TestTypedSignatures:
    """Tests for DSPy 3.x typed signatures with Pydantic models."""

    @pytest.fixture
    def typed_reasoner(self):
        """
        Create a DSPyReasoner configured for typed signatures and an enabled routing cache.

        Returns:
            reasoner (DSPyReasoner): A DSPyReasoner instance with use_enhanced_signatures=True, use_typed_signatures=True, enable_routing_cache=True, and cache_ttl_seconds=300.
        """
        return DSPyReasoner(
            use_enhanced_signatures=True,
            use_typed_signatures=True,
            enable_routing_cache=True,
            cache_ttl_seconds=300,
        )

    @pytest.fixture
    def untyped_reasoner(self):
        """
        Create a DSPyReasoner configured to use enhanced signatures with typed signatures and the routing cache disabled.

        Returns:
            DSPyReasoner: An instance with enhanced signatures enabled, typed signatures disabled, and routing cache disabled.
        """
        return DSPyReasoner(
            use_enhanced_signatures=True,
            use_typed_signatures=False,
            enable_routing_cache=False,
        )

    def test_typed_signatures_enabled_by_default(self, typed_reasoner):
        """Verify typed signatures are enabled by default."""
        assert typed_reasoner.use_typed_signatures is True

    def test_typed_signatures_can_be_disabled(self, untyped_reasoner):
        """Verify typed signatures can be disabled."""
        assert untyped_reasoner.use_typed_signatures is False

    def test_routing_cache_initialized(self, typed_reasoner):
        """Verify routing cache is initialized."""
        assert hasattr(typed_reasoner, "_routing_cache")
        assert isinstance(typed_reasoner._routing_cache, dict)

    def test_cache_settings_stored(self, typed_reasoner):
        """Verify cache settings are stored."""
        assert typed_reasoner.enable_routing_cache is True
        assert typed_reasoner.cache_ttl_seconds == 300


class TestRoutingCache:
    """Tests for routing cache functionality."""

    @pytest.fixture
    def cached_reasoner(self):
        """
        Create a DSPyReasoner configured with routing cache enabled.

        Returns:
            DSPyReasoner: A reasoner with enhanced signatures enabled, typed signatures disabled, routing cache enabled, and a 60-second cache TTL.
        """
        r = DSPyReasoner(
            use_enhanced_signatures=True,
            use_typed_signatures=False,
            enable_routing_cache=True,
            cache_ttl_seconds=60,
        )
        return r

    def test_cache_key_generation(self, cached_reasoner):
        """Verify cache keys are generated consistently."""
        # The cache key should be deterministic for same inputs
        key1 = cached_reasoner._get_cache_key("Test task", "Writer,Researcher")
        key2 = cached_reasoner._get_cache_key("Test task", "Writer,Researcher")

        assert key1 == key2
        assert len(key1) == 16  # MD5 hex digest truncated to 16 chars

    def test_different_tasks_different_keys(self, cached_reasoner):
        """Verify different tasks produce different cache keys."""
        key1 = cached_reasoner._get_cache_key("Task A", "Writer")
        key2 = cached_reasoner._get_cache_key("Task B", "Writer")

        assert key1 != key2

    def test_cache_miss_returns_none(self, cached_reasoner):
        """Verify cache miss returns None."""
        result = cached_reasoner._get_cached_routing("nonexistent_key")

        assert result is None

    def test_cache_hit_returns_result(self, cached_reasoner):
        """Verify cache hit returns cached result."""
        # Manually populate cache
        cached_reasoner._routing_cache["test_key"] = {
            "result": {"assigned_to": ["Writer"]},
            "timestamp": time.time(),
        }

        result = cached_reasoner._get_cached_routing("test_key")

        assert result is not None
        assert result["assigned_to"] == ["Writer"]

    def test_expired_cache_returns_none(self, cached_reasoner):
        """Verify expired cache entries return None."""
        # Set TTL to 1 second for this test
        cached_reasoner.cache_ttl_seconds = 1

        # Add expired entry
        cached_reasoner._routing_cache["expired_key"] = {
            "result": {"assigned_to": ["Writer"]},
            "timestamp": time.time() - 10,  # 10 seconds ago
        }

        result = cached_reasoner._get_cached_routing("expired_key")

        assert result is None

    def test_cache_stores_result(self, cached_reasoner):
        """Verify _cache_routing stores results correctly."""
        result = {"assigned_to": ["Researcher"], "mode": "delegated"}

        cached_reasoner._cache_routing("new_key", result)

        assert "new_key" in cached_reasoner._routing_cache
        assert cached_reasoner._routing_cache["new_key"]["result"] == result

    def test_clear_routing_cache(self, cached_reasoner):
        """Verify clear_routing_cache empties the cache."""
        # Add some entries
        cached_reasoner._routing_cache["key1"] = {"result": {}, "timestamp": time.time()}
        cached_reasoner._routing_cache["key2"] = {"result": {}, "timestamp": time.time()}

        cached_reasoner.clear_routing_cache()

        assert len(cached_reasoner._routing_cache) == 0


class TestTypedRoutingExtraction:
    """Tests for typed routing decision extraction."""

    @pytest.fixture
    def reasoner(self):
        """
        Create a DSPyReasoner configured with enhanced and typed signatures for extraction tests.

        Returns:
            DSPyReasoner: A reasoner instance with `use_enhanced_signatures=True` and `use_typed_signatures=True`.
        """
        return DSPyReasoner(
            use_enhanced_signatures=True,
            use_typed_signatures=True,
        )

    def test_extract_from_pydantic_model(self, reasoner):
        """Verify extraction works with Pydantic model output."""
        from agentic_fleet.dspy_modules.typed_models import RoutingDecisionOutput

        # Create a mock prediction with Pydantic model
        model_output = RoutingDecisionOutput(
            assigned_to=["Writer", "Researcher"],
            execution_mode="sequential",
            subtasks=["Research", "Write"],
            tool_requirements=["TavilySearchTool"],
            reasoning="Multi-step task",
        )

        mock_pred = MockPrediction(decision=model_output)

        result = reasoner._extract_typed_routing_decision(mock_pred)

        assert result["assigned_to"] == ["Writer", "Researcher"]
        assert result["execution_mode"] == "sequential"
        assert result["tool_requirements"] == ["TavilySearchTool"]

    def test_extract_from_dict_attribute(self, reasoner):
        """Verify extraction works when decision is a dict."""

        # Create a mock object with model_dump method to simulate Pydantic
        class MockDecision:
            def model_dump(self):
                """
                Return a serialized routing decision as a plain dictionary.

                Returns:
                    dict: A routing decision mapping with the following keys:
                        - assigned_to (list[str]): Roles or assignees selected for the task.
                        - execution_mode (str): Execution mode for the task (e.g., "delegated").
                        - subtasks (list): List of subtasks, empty if none.
                        - tool_requirements (list): Tool requirement descriptors, empty if none.
                        - reasoning (str): Human-readable explanation of the routing decision.
                """
                return {
                    "assigned_to": ["Analyst"],
                    "execution_mode": "delegated",
                    "subtasks": [],
                    "tool_requirements": [],
                    "reasoning": "Analysis task",
                }

        mock_pred = MockPrediction(decision=MockDecision())

        result = reasoner._extract_typed_routing_decision(mock_pred)

        assert result["assigned_to"] == ["Analyst"]
        assert result["execution_mode"] == "delegated"

    def test_extract_fallback_to_direct_attributes(self, reasoner):
        """Verify extraction falls back to direct attributes."""
        mock_pred = MockPrediction(
            assigned_to=["Writer"],
            execution_mode="delegated",
            subtasks=["Write"],
            tool_requirements=[],
            reasoning="Direct attributes",
        )

        result = reasoner._extract_typed_routing_decision(mock_pred)

        assert result["assigned_to"] == ["Writer"]
        assert result["execution_mode"] == "delegated"


class TestBackwardCompatibility:
    """Tests for backward compatibility with older serialized models."""

    def test_deserialized_reasoner_missing_new_attributes(self):
        """Verify deserialized reasoner handles missing new attributes."""
        # Simulate a deserialized reasoner missing new attributes
        r = DSPyReasoner.__new__(DSPyReasoner)
        r.use_enhanced_signatures = True
        r._analyzer = None
        r._router = None
        # Missing: use_typed_signatures, enable_routing_cache, etc.

        # _ensure_modules_initialized should add missing attributes
        r._ensure_modules_initialized()

        assert hasattr(r, "use_typed_signatures")
        assert hasattr(r, "enable_routing_cache")
        assert hasattr(r, "_routing_cache")

    def test_legacy_reasoner_defaults_to_untyped(self):
        """Verify legacy reasoner defaults to untyped signatures."""
        r = DSPyReasoner.__new__(DSPyReasoner)
        r.use_enhanced_signatures = False
        r._modules_initialized = False

        # Simulate missing typed signature attribute
        r._ensure_modules_initialized()

        # Should default to False for typed signatures
        assert r.use_typed_signatures is False
