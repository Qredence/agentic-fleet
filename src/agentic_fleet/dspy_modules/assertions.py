"""DSPy assertions for validating routing decisions.

This module provides DSPy-compatible assertions and suggestions for routing validation.
Assertions are used during optimization to guide the model toward better outputs.

DSPy 3.x Note:
- dspy.Assert: Hard constraint - causes backtracking on failure
- dspy.Suggest: Soft constraint - guides optimization but doesn't fail

Assertion Categories:
1. Agent Assignment Validation - ensure agents exist and are appropriate
2. Tool Assignment Validation - ensure tools exist and match task needs
3. Execution Mode Validation - ensure mode matches agent count
4. Task-Type Specific - domain-specific routing rules
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

import dspy

from agentic_fleet.utils.models import ExecutionMode, RoutingDecision

logger = logging.getLogger(__name__)

# --- DSPy Assertion Setup ---

if TYPE_CHECKING:
    # Mock for type checking if dspy stubs are missing Suggest/Assert
    def Suggest(condition: bool, message: str) -> None:  # noqa: N802, D103
        pass

    def Assert(condition: bool, message: str) -> None:  # noqa: N802, D103
        pass

else:
    Suggest = getattr(dspy, "Suggest", None)
    Assert = getattr(dspy, "Assert", None)

    if Suggest is None:
        logger.debug(
            "dspy.Suggest is not available; soft assertions will be skipped. "
            "Constraints should be learned via GEPA optimization instead."
        )

        def Suggest(condition: bool, message: str) -> None:  # noqa: N802, D103
            pass

    if Assert is None:
        logger.debug(
            "dspy.Assert is not available; hard assertions will be skipped. "
            "Use typed signatures for validation instead."
        )

        def Assert(condition: bool, message: str) -> None:  # noqa: N802, D103
            pass


# --- Agent Assignment Assertions ---


def validate_agent_exists(
    assigned_agents: list[str] | tuple[str, ...],
    available_agents: list[str] | tuple[str, ...],
) -> bool:
    """Validate that all assigned agents exist in the available team.

    Args:
        assigned_agents: List of agent names assigned to the task
        available_agents: List of agent names available in the team

    Returns:
        True if all assigned agents exist, False otherwise
    """
    available_set = {a.lower() for a in available_agents}
    return all(agent.lower() in available_set for agent in assigned_agents)


def assert_valid_agents(
    assigned_agents: list[str] | tuple[str, ...],
    available_agents: list[str] | tuple[str, ...],
) -> None:
    """Assert that all assigned agents exist (hard constraint).

    This should be used during routing to ensure agents are valid.
    Triggers backtracking if assertion fails.
    """
    Assert(
        validate_agent_exists(assigned_agents, available_agents),
        f"All assigned agents must exist in the team. "
        f"Assigned: {list(assigned_agents)}, Available: {list(available_agents)}",
    )


def suggest_valid_agents(
    assigned_agents: list[str] | tuple[str, ...],
    available_agents: list[str] | tuple[str, ...],
) -> None:
    """Suggest that all assigned agents should exist (soft constraint).

    Use this when you want to guide optimization without hard failures.
    """
    Suggest(
        validate_agent_exists(assigned_agents, available_agents),
        f"Assigned agents should exist in the team. Available agents: {list(available_agents)}",
    )


# --- Tool Assignment Assertions ---


def validate_tool_assignment(
    assigned_tools: list[str] | tuple[str, ...],
    available_tools: list[str] | tuple[str, ...],
) -> bool:
    """Validate that all assigned tools exist in available tools.

    Args:
        assigned_tools: List of tool names assigned to the task
        available_tools: List of tool names available

    Returns:
        True if all assigned tools exist, False otherwise
    """
    available_set = {t.lower() for t in available_tools}
    return all(tool.lower() in available_set for tool in assigned_tools)


def assert_valid_tools(
    assigned_tools: list[str] | tuple[str, ...],
    available_tools: list[str] | tuple[str, ...],
) -> None:
    """Assert that all assigned tools exist (hard constraint)."""
    Assert(
        validate_tool_assignment(assigned_tools, available_tools),
        f"All assigned tools must exist. "
        f"Assigned: {list(assigned_tools)}, Available: {list(available_tools)}",
    )


def suggest_valid_tools(
    assigned_tools: list[str] | tuple[str, ...],
    available_tools: list[str] | tuple[str, ...],
) -> None:
    """Suggest that all assigned tools should exist (soft constraint)."""
    Suggest(
        validate_tool_assignment(assigned_tools, available_tools),
        f"Assigned tools should exist. Available tools: {list(available_tools)}",
    )


# --- Execution Mode Assertions ---


def validate_mode_agent_match(
    mode: ExecutionMode | str,
    agent_count: int,
) -> bool:
    """Validate that execution mode matches agent count.

    Rules:
    - DELEGATED: requires exactly 1 agent
    - SEQUENTIAL/PARALLEL: requires 1+ agents (allows single agent for efficiency)
    - GROUP_CHAT/DISCUSSION: requires 2+ agents

    Args:
        mode: The execution mode
        agent_count: Number of assigned agents

    Returns:
        True if mode matches agent count, False otherwise
    """
    if isinstance(mode, str):
        mode = ExecutionMode.from_raw(mode)

    if mode == ExecutionMode.DELEGATED:
        return agent_count == 1
    elif mode in (ExecutionMode.SEQUENTIAL, ExecutionMode.PARALLEL):
        return agent_count >= 1  # Allow single agent for efficiency
    elif mode in (ExecutionMode.GROUP_CHAT, ExecutionMode.DISCUSSION):
        return agent_count >= 2
    return True


def assert_mode_agent_consistency(
    mode: ExecutionMode | str,
    agent_count: int,
) -> None:
    """Assert that execution mode is consistent with agent count (hard constraint)."""
    mode_enum = ExecutionMode.from_raw(mode) if isinstance(mode, str) else mode

    if mode_enum == ExecutionMode.DELEGATED:
        Assert(
            agent_count == 1,
            f"DELEGATED mode requires exactly 1 agent, but {agent_count} were assigned.",
        )
    elif mode_enum in (ExecutionMode.GROUP_CHAT, ExecutionMode.DISCUSSION):
        Assert(
            agent_count >= 2,
            f"{mode_enum.value} mode requires at least 2 agents, but {agent_count} were assigned.",
        )


def suggest_mode_agent_consistency(
    mode: ExecutionMode | str,
    agent_count: int,
) -> None:
    """Suggest that execution mode should match agent count (soft constraint)."""
    Suggest(
        validate_mode_agent_match(mode, agent_count),
        f"Execution mode should match agent count. Mode: {mode}, Agent count: {agent_count}",
    )


# --- Task-Type Specific Assertions ---


RESEARCH_KEYWORDS = frozenset(
    [
        "research",
        "find",
        "search",
        "look up",
        "investigate",
        "explore",
        "latest",
        "current",
        "recent",
        "today",
        "news",
        "update",
        "what is",
        "who is",
        "when did",
        "where is",
        "how does",
    ]
)

CODING_KEYWORDS = frozenset(
    [
        "code",
        "program",
        "implement",
        "function",
        "class",
        "debug",
        "fix bug",
        "write script",
        "develop",
        "build",
        "create app",
        "refactor",
        "optimize code",
        "algorithm",
    ]
)

ANALYSIS_KEYWORDS = frozenset(
    [
        "analyze",
        "analysis",
        "calculate",
        "compute",
        "math",
        "statistics",
        "data",
        "chart",
        "graph",
        "visualize",
        "summarize",
        "evaluate",
        "assess",
        "compare",
    ]
)

WRITING_KEYWORDS = frozenset(
    [
        "write",
        "draft",
        "compose",
        "create content",
        "blog",
        "article",
        "essay",
        "email",
        "report",
        "document",
        "describe",
        "explain",
        "summarize",
    ]
)


def detect_task_type(task: str) -> str:
    """Detect the primary task type from task description.

    Args:
        task: The task description

    Returns:
        Task type: "research", "coding", "analysis", "writing", or "general"
    """
    task_lower = task.lower()

    if any(kw in task_lower for kw in RESEARCH_KEYWORDS):
        return "research"
    if any(kw in task_lower for kw in CODING_KEYWORDS):
        return "coding"
    if any(kw in task_lower for kw in ANALYSIS_KEYWORDS):
        return "analysis"
    if any(kw in task_lower for kw in WRITING_KEYWORDS):
        return "writing"
    return "general"


def suggest_task_type_routing(
    task: str,
    assigned_agents: list[str] | tuple[str, ...],
    tool_requirements: list[str] | tuple[str, ...],
) -> None:
    """Apply task-type specific routing suggestions.

    Args:
        task: The task description
        assigned_agents: List of assigned agent names
        tool_requirements: List of required tool names
    """
    task_type = detect_task_type(task)
    agents_lower = [a.lower() for a in assigned_agents]
    tools_lower = [t.lower() for t in tool_requirements]

    if task_type == "research":
        # Research tasks should use search tools
        has_search_tool = any("search" in t or "tavily" in t or "browser" in t for t in tools_lower)
        Suggest(
            has_search_tool,
            "Research tasks should include a search tool (Tavily, Browser) for external information.",
        )
        # Research tasks should include Researcher agent
        has_researcher = any("research" in a for a in agents_lower)
        Suggest(
            has_researcher,
            "Research tasks should typically involve a Researcher agent.",
        )

    elif task_type == "coding":
        # Coding tasks should use code interpreter
        has_code_tool = any(
            "code" in t or "interpreter" in t or "sandbox" in t for t in tools_lower
        )
        Suggest(
            has_code_tool,
            "Coding tasks should include a code execution tool (CodeInterpreter, Sandbox).",
        )
        # Coding tasks should include Coder agent
        has_coder = any("coder" in a or "developer" in a for a in agents_lower)
        Suggest(
            has_coder,
            "Coding tasks should typically involve a Coder agent.",
        )

    elif task_type == "analysis":
        # Analysis tasks should use code interpreter for calculations
        has_analysis_tool = any(
            "code" in t or "interpreter" in t or "data" in t for t in tools_lower
        )
        Suggest(
            has_analysis_tool,
            "Analysis tasks should include tools for computation (CodeInterpreter).",
        )
        # Analysis tasks should include Analyst agent
        has_analyst = any("analyst" in a for a in agents_lower)
        Suggest(
            has_analyst,
            "Analysis tasks should typically involve an Analyst agent.",
        )

    elif task_type == "writing":
        # Writing tasks typically don't need special tools
        # But should include Writer agent
        has_writer = any("writer" in a for a in agents_lower)
        Suggest(
            has_writer,
            "Writing tasks should typically involve a Writer agent.",
        )


# --- Comprehensive Validation ---


def validate_routing_decision(decision: RoutingDecision, task: str) -> None:
    """Apply DSPy assertions to validate and refine routing decisions.

    This is the main validation function that applies all relevant constraints.

    Args:
        decision: The routing decision to validate.
        task: The original task description.
    """
    # Hard constraint: At least one agent must be assigned
    Assert(
        len(decision.assigned_to) > 0,
        "At least one agent must be assigned to the task.",
    )

    # Soft constraints for mode/agent consistency
    suggest_mode_agent_consistency(decision.mode, len(decision.assigned_to))

    # Apply task-type specific suggestions
    suggest_task_type_routing(
        task,
        list(decision.assigned_to),
        list(decision.tool_requirements),
    )

    # Legacy constraints (kept for backward compatibility)
    task_lower = task.lower()

    # Constraint: Research tasks need search tools
    if any(kw in task_lower for kw in ["research", "find", "search", "latest", "current"]):
        Suggest(
            "tavilysearchtool" in [t.lower() for t in decision.tool_requirements],
            "Research tasks require the TavilySearchTool to access external information.",
        )

    # Constraint: Calculation tasks need code interpreter
    if any(kw in task_lower for kw in ["calculate", "compute", "math", "analysis"]):
        Suggest(
            "hostedcodeinterpretertool" in [t.lower() for t in decision.tool_requirements],
            "Calculation and analysis tasks require the HostedCodeInterpreterTool.",
        )

    # Constraint: Multi-agent tasks cannot be delegated
    if len(decision.assigned_to) > 1:
        Suggest(
            decision.mode != ExecutionMode.DELEGATED,
            "Tasks assigned to multiple agents must use SEQUENTIAL or PARALLEL execution mode, not DELEGATED.",
        )

    # Constraint: Single-agent tasks should be delegated (soft suggestion)
    if len(decision.assigned_to) == 1:
        Suggest(
            decision.mode == ExecutionMode.DELEGATED,
            "Single-agent tasks should typically use DELEGATED execution mode for efficiency.",
        )


def validate_full_routing(
    decision: RoutingDecision | dict[str, Any],
    task: str,
    available_agents: list[str] | None = None,
    available_tools: list[str] | None = None,
) -> None:
    """Comprehensive routing validation with all available context.

    This function applies both hard assertions and soft suggestions based on
    the full routing context including available agents and tools.

    Args:
        decision: The routing decision (RoutingDecision or dict)
        task: The original task description
        available_agents: Optional list of available agent names
        available_tools: Optional list of available tool names
    """
    # Convert dict to RoutingDecision if needed
    routing_decision: RoutingDecision
    if isinstance(decision, dict):
        routing_decision = RoutingDecision.from_mapping(cast(dict[str, Any], decision))
    else:
        routing_decision = decision
    decision = routing_decision

    # Validate basic routing decision
    validate_routing_decision(decision, task)

    # Validate agents exist (if available_agents provided)
    if available_agents:
        suggest_valid_agents(list(decision.assigned_to), available_agents)

    # Validate tools exist (if available_tools provided)
    if available_tools and decision.tool_requirements:
        suggest_valid_tools(list(decision.tool_requirements), available_tools)


# --- Assertion Decorators for Module Wrapping ---


def with_routing_assertions(_max_backtracks: int = 2):
    """Decorator to wrap a DSPy module with routing assertions.

    Usage:
        @with_routing_assertions(max_backtracks=3)
        def route_task(...):
            ...

    Args:
        _max_backtracks: Maximum number of assertion retries (reserved for future use)

    Returns:
        Decorator function
    """

    # Note: _max_backtracks is reserved for future use when dspy.assert_transform_module
    # supports configurable backtracking limits
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Import here to avoid circular imports
            import dspy

            # Check if assertion transform is available
            transform = getattr(dspy, "assert_transform_module", None)
            if transform is None:
                # Fall back to direct execution
                return func(*args, **kwargs)

            # Wrap with assertion transform
            @transform
            def wrapped_func(*a, **kw):
                return func(*a, **kw)

            return wrapped_func(*args, **kwargs)

        return wrapper

    return decorator
