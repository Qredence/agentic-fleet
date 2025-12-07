"""Tests for DSPy assertions and routing validation.

These tests verify that the assertion functions correctly validate
routing decisions, agent assignments, tool assignments, and task-type
specific routing rules.
"""

from __future__ import annotations

from unittest.mock import patch

from agentic_fleet.dspy_modules.assertions import (
    ANALYSIS_KEYWORDS,
    CODING_KEYWORDS,
    RESEARCH_KEYWORDS,
    WRITING_KEYWORDS,
    assert_mode_agent_consistency,
    assert_valid_agents,
    assert_valid_tools,
    detect_task_type,
    suggest_mode_agent_consistency,
    suggest_task_type_routing,
    suggest_valid_agents,
    suggest_valid_tools,
    validate_agent_exists,
    validate_full_routing,
    validate_mode_agent_match,
    validate_routing_decision,
    validate_tool_assignment,
    with_routing_assertions,
)
from agentic_fleet.utils.models import ExecutionMode, RoutingDecision


class TestValidateAgentExists:
    """Tests for agent existence validation."""

    def test_all_agents_exist(self):
        """Verify returns True when all assigned agents exist."""
        assigned = ["Writer", "Researcher"]
        available = ["Writer", "Researcher", "Analyst"]

        result = validate_agent_exists(assigned, available)

        assert result is True

    def test_agent_missing(self):
        """Verify returns False when agent is missing."""
        assigned = ["Writer", "Coder"]
        available = ["Writer", "Researcher"]

        result = validate_agent_exists(assigned, available)

        assert result is False

    def test_case_insensitive(self):
        """Verify validation is case-insensitive."""
        assigned = ["WRITER", "researcher"]
        available = ["Writer", "Researcher"]

        result = validate_agent_exists(assigned, available)

        assert result is True

    def test_empty_assigned(self):
        """Verify returns True when no agents assigned."""
        assigned = []
        available = ["Writer", "Researcher"]

        result = validate_agent_exists(assigned, available)

        assert result is True

    def test_tuple_input(self):
        """Verify works with tuple inputs."""
        assigned = ("Writer",)
        available = ("Writer", "Researcher")

        result = validate_agent_exists(assigned, available)

        assert result is True


class TestValidateToolAssignment:
    """Tests for tool assignment validation."""

    def test_all_tools_exist(self):
        """Verify returns True when all assigned tools exist."""
        assigned = ["TavilySearchTool", "CodeInterpreter"]
        available = ["TavilySearchTool", "CodeInterpreter", "Browser"]

        result = validate_tool_assignment(assigned, available)

        assert result is True

    def test_tool_missing(self):
        """Verify returns False when tool is missing."""
        assigned = ["TavilySearchTool", "ImageGenerator"]
        available = ["TavilySearchTool", "CodeInterpreter"]

        result = validate_tool_assignment(assigned, available)

        assert result is False

    def test_case_insensitive(self):
        """Verify validation is case-insensitive."""
        assigned = ["TAVILYSEARCHTOOL"]
        available = ["TavilySearchTool"]

        result = validate_tool_assignment(assigned, available)

        assert result is True


class TestValidateModeAgentMatch:
    """Tests for execution mode / agent count validation."""

    def test_delegated_single_agent(self):
        """Verify DELEGATED requires exactly 1 agent."""
        result = validate_mode_agent_match(ExecutionMode.DELEGATED, 1)
        assert result is True

        result = validate_mode_agent_match(ExecutionMode.DELEGATED, 2)
        assert result is False

    def test_sequential_multiple_agents(self):
        """Verify SEQUENTIAL works with 1+ agents."""
        result = validate_mode_agent_match(ExecutionMode.SEQUENTIAL, 1)
        assert result is True

        result = validate_mode_agent_match(ExecutionMode.SEQUENTIAL, 3)
        assert result is True

    def test_parallel_multiple_agents(self):
        """Verify PARALLEL works with 1+ agents."""
        result = validate_mode_agent_match(ExecutionMode.PARALLEL, 2)
        assert result is True

    def test_group_chat_requires_multiple(self):
        """Verify GROUP_CHAT requires 2+ agents."""
        result = validate_mode_agent_match(ExecutionMode.GROUP_CHAT, 1)
        assert result is False

        result = validate_mode_agent_match(ExecutionMode.GROUP_CHAT, 2)
        assert result is True

    def test_discussion_requires_multiple(self):
        """Verify DISCUSSION requires 2+ agents."""
        result = validate_mode_agent_match(ExecutionMode.DISCUSSION, 1)
        assert result is False

        result = validate_mode_agent_match(ExecutionMode.DISCUSSION, 3)
        assert result is True

    def test_string_mode_input(self):
        """Verify string mode is converted to enum."""
        result = validate_mode_agent_match("delegated", 1)
        assert result is True


class TestDetectTaskType:
    """Tests for task type detection."""

    def test_research_task_detected(self):
        """Verify research tasks are detected."""
        tasks = [
            "Research quantum computing trends",
            "Find the latest AI papers",
            "Search for climate data",
            "What is the latest news on Python?",
        ]

        for task in tasks:
            result = detect_task_type(task)
            assert result == "research", f"Failed for: {task}"

    def test_coding_task_detected(self):
        """Verify coding tasks are detected."""
        tasks = [
            "Write a Python function to sort arrays",
            "Debug the login code",
            "Implement a REST API",
            "Refactor the database module",
        ]

        for task in tasks:
            result = detect_task_type(task)
            assert result == "coding", f"Failed for: {task}"

    def test_analysis_task_detected(self):
        """Verify analysis tasks are detected."""
        tasks = [
            "Analyze the sales data",
            "Calculate the average response time",
            "Create a chart of user growth",
            "Summarize the quarterly report",
        ]

        for task in tasks:
            result = detect_task_type(task)
            assert result == "analysis", f"Failed for: {task}"

    def test_writing_task_detected(self):
        """Verify writing tasks are detected."""
        tasks = [
            "Write a blog post about AI",
            "Draft an email to the team",
            "Compose a marketing copy",
            "Create a technical document",
        ]

        for task in tasks:
            result = detect_task_type(task)
            assert result == "writing", f"Failed for: {task}"

    def test_general_task_fallback(self):
        """Verify general tasks fall back to 'general'."""
        tasks = [
            "Hello, how are you?",
            "Thanks for your help",
            "Schedule a meeting",
        ]

        for task in tasks:
            result = detect_task_type(task)
            assert result == "general", f"Failed for: {task}"


class TestSuggestTaskTypeRouting:
    """Tests for task-type specific routing suggestions."""

    def test_research_task_suggests_search_tool(self):
        """Verify research tasks suggest search tools."""
        # Mock Suggest to capture calls
        with patch("agentic_fleet.dspy_modules.assertions.Suggest") as mock_suggest:
            suggest_task_type_routing(
                task="Research the latest AI trends",
                assigned_agents=["Researcher"],
                tool_requirements=["TavilySearchTool"],
            )

            # Should suggest search tool is present
            assert mock_suggest.call_count >= 1

    def test_coding_task_suggests_code_tool(self):
        """Verify coding tasks suggest code interpreter."""
        with patch("agentic_fleet.dspy_modules.assertions.Suggest") as mock_suggest:
            suggest_task_type_routing(
                task="Write a function to parse JSON",
                assigned_agents=["Coder"],
                tool_requirements=["CodeInterpreter"],
            )

            assert mock_suggest.call_count >= 1

    def test_analysis_task_suggests_analyst(self):
        """Verify analysis tasks suggest analyst agent."""
        with patch("agentic_fleet.dspy_modules.assertions.Suggest") as mock_suggest:
            suggest_task_type_routing(
                task="Analyze the data trends",
                assigned_agents=["Analyst"],
                tool_requirements=["CodeInterpreter"],
            )

            assert mock_suggest.call_count >= 1


class TestValidateRoutingDecision:
    """Tests for comprehensive routing validation."""

    def test_valid_routing_decision(self):
        """Verify valid routing decision passes validation."""
        decision = RoutingDecision(
            task="Write something",
            assigned_to=("Writer",),
            mode=ExecutionMode.DELEGATED,
            subtasks=("Write",),
            tool_requirements=(),
        )

        # Should not raise
        with patch("agentic_fleet.dspy_modules.assertions.Assert") as mock_assert:
            with patch("agentic_fleet.dspy_modules.assertions.Suggest"):
                validate_routing_decision(decision, "Write something")

            # Assert should be called with at least one agent
            mock_assert.assert_called()

    def test_empty_assigned_to_fails(self):
        """Verify empty assigned_to triggers assertion."""
        decision = RoutingDecision(
            task="Some task",
            assigned_to=(),
            mode=ExecutionMode.DELEGATED,
            subtasks=(),
            tool_requirements=(),
        )

        with patch("agentic_fleet.dspy_modules.assertions.Assert") as mock_assert:
            with patch("agentic_fleet.dspy_modules.assertions.Suggest"):
                validate_routing_decision(decision, "Some task")

            # Assert should be called with False condition
            call_args = mock_assert.call_args_list[0]
            assert call_args[0][0] is False  # First arg is the condition


class TestValidateFullRouting:
    """Tests for full routing validation with context."""

    def test_validates_with_available_agents(self):
        """Verify validation uses available agents list."""
        decision = RoutingDecision(
            task="Write something",
            assigned_to=("Writer",),
            mode=ExecutionMode.DELEGATED,
            subtasks=(),
            tool_requirements=(),
        )

        with (
            patch("agentic_fleet.dspy_modules.assertions.Assert"),
            patch("agentic_fleet.dspy_modules.assertions.Suggest") as mock_suggest,
        ):
            validate_full_routing(
                decision=decision,
                task="Write something",
                available_agents=["Writer", "Researcher"],
            )

            # Suggest should be called for agent validation
            assert mock_suggest.call_count >= 1

    def test_validates_with_available_tools(self):
        """Verify validation uses available tools list."""
        decision = RoutingDecision(
            task="Research topic",
            assigned_to=("Researcher",),
            mode=ExecutionMode.DELEGATED,
            subtasks=(),
            tool_requirements=("TavilySearchTool",),
        )

        with (
            patch("agentic_fleet.dspy_modules.assertions.Assert"),
            patch("agentic_fleet.dspy_modules.assertions.Suggest") as mock_suggest,
        ):
            validate_full_routing(
                decision=decision,
                task="Research topic",
                available_agents=["Researcher"],
                available_tools=["TavilySearchTool", "Browser"],
            )

            assert mock_suggest.call_count >= 1

    def test_accepts_dict_input(self):
        """Verify validation accepts dict input."""
        decision_dict = {
            "task": "Test task",
            "assigned_to": ["Writer"],
            "mode": "delegated",
            "subtasks": [],
            "tool_requirements": [],
        }

        with (
            patch("agentic_fleet.dspy_modules.assertions.Assert"),
            patch("agentic_fleet.dspy_modules.assertions.Suggest"),
        ):
            # Should not raise
            validate_full_routing(
                decision=decision_dict,
                task="Test task",
            )


class TestAssertFunctions:
    """Tests for hard assertion functions."""

    def test_assert_valid_agents_with_valid_agents(self):
        """Verify assert_valid_agents passes with valid agents."""
        with patch("agentic_fleet.dspy_modules.assertions.Assert") as mock_assert:
            assert_valid_agents(["Writer"], ["Writer", "Researcher"])

            mock_assert.assert_called_once()
            # First argument should be True (condition passes)
            assert mock_assert.call_args[0][0] is True

    def test_assert_valid_agents_with_invalid_agents(self):
        """Verify assert_valid_agents fails with invalid agents."""
        with patch("agentic_fleet.dspy_modules.assertions.Assert") as mock_assert:
            assert_valid_agents(["NonExistent"], ["Writer", "Researcher"])

            mock_assert.assert_called_once()
            # First argument should be False (condition fails)
            assert mock_assert.call_args[0][0] is False

    def test_assert_valid_tools_with_valid_tools(self):
        """Verify assert_valid_tools passes with valid tools."""
        with patch("agentic_fleet.dspy_modules.assertions.Assert") as mock_assert:
            assert_valid_tools(["TavilySearchTool"], ["TavilySearchTool", "Browser"])

            mock_assert.assert_called_once()
            assert mock_assert.call_args[0][0] is True

    def test_assert_mode_agent_consistency_delegated(self):
        """Verify assert_mode_agent_consistency for DELEGATED mode."""
        with patch("agentic_fleet.dspy_modules.assertions.Assert") as mock_assert:
            assert_mode_agent_consistency(ExecutionMode.DELEGATED, 1)

            # Should assert that agent_count == 1
            assert mock_assert.call_args[0][0] is True

    def test_assert_mode_agent_consistency_delegated_fails(self):
        """Verify assert_mode_agent_consistency fails for DELEGATED with multiple agents."""
        with patch("agentic_fleet.dspy_modules.assertions.Assert") as mock_assert:
            assert_mode_agent_consistency(ExecutionMode.DELEGATED, 2)

            # Should fail because DELEGATED requires exactly 1 agent
            assert mock_assert.call_args[0][0] is False


class TestSuggestFunctions:
    """Tests for soft suggestion functions."""

    def test_suggest_valid_agents(self):
        """Verify suggest_valid_agents calls Suggest."""
        with patch("agentic_fleet.dspy_modules.assertions.Suggest") as mock_suggest:
            suggest_valid_agents(["Writer"], ["Writer", "Researcher"])

            mock_suggest.assert_called_once()

    def test_suggest_valid_tools(self):
        """Verify suggest_valid_tools calls Suggest."""
        with patch("agentic_fleet.dspy_modules.assertions.Suggest") as mock_suggest:
            suggest_valid_tools(["Browser"], ["TavilySearchTool", "Browser"])

            mock_suggest.assert_called_once()

    def test_suggest_mode_agent_consistency(self):
        """Verify suggest_mode_agent_consistency calls Suggest."""
        with patch("agentic_fleet.dspy_modules.assertions.Suggest") as mock_suggest:
            suggest_mode_agent_consistency(ExecutionMode.SEQUENTIAL, 2)

            mock_suggest.assert_called_once()


class TestWithRoutingAssertionsDecorator:
    """Tests for the routing assertions decorator."""

    def test_decorator_wraps_function(self):
        """Verify decorator wraps the function correctly."""

        @with_routing_assertions()
        def dummy_route(task: str) -> dict:
            """
            Create a simple routing response containing the original task and assigned agents.

            Returns:
                routing (dict): Dictionary with keys "task" (the provided task string) and "assigned_to" (list of agent names assigned to the task).
            """
            return {"task": task, "assigned_to": ["Writer"]}

        result = dummy_route("Test task")

        assert result["task"] == "Test task"
        assert result["assigned_to"] == ["Writer"]

    def test_decorator_with_max_backtracks(self):
        """Verify decorator accepts max_backtracks parameter."""

        @with_routing_assertions(_max_backtracks=5)
        def dummy_route(task: str) -> dict:
            """
            Produce a simple routing decision assigning the task to a default writer.

            Returns:
                dict: A routing decision containing the key "assigned_to" whose value is a list of agent names (e.g., ["Writer"]).
            """
            return {"assigned_to": ["Writer"]}

        result = dummy_route("Test")

        assert "assigned_to" in result


class TestKeywordSets:
    """Tests for keyword sets used in task detection."""

    def test_research_keywords_not_empty(self):
        """Verify RESEARCH_KEYWORDS is populated."""
        assert len(RESEARCH_KEYWORDS) > 0
        assert "research" in RESEARCH_KEYWORDS

    def test_coding_keywords_not_empty(self):
        """Verify CODING_KEYWORDS is populated."""
        assert len(CODING_KEYWORDS) > 0
        assert "code" in CODING_KEYWORDS

    def test_analysis_keywords_not_empty(self):
        """Verify ANALYSIS_KEYWORDS is populated."""
        assert len(ANALYSIS_KEYWORDS) > 0
        assert "analyze" in ANALYSIS_KEYWORDS

    def test_writing_keywords_not_empty(self):
        """Verify WRITING_KEYWORDS is populated."""
        assert len(WRITING_KEYWORDS) > 0
        assert "write" in WRITING_KEYWORDS

    def test_keyword_sets_are_frozen(self):
        """Verify keyword sets are immutable."""
        assert isinstance(RESEARCH_KEYWORDS, frozenset)
        assert isinstance(CODING_KEYWORDS, frozenset)
        assert isinstance(ANALYSIS_KEYWORDS, frozenset)
        assert isinstance(WRITING_KEYWORDS, frozenset)
