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
    def Suggest(condition: bool, message: str) -> None:  # noqa: N802
        """
        Register a soft routing suggestion associated with a boolean condition and a human-readable message.

        Parameters:
            condition (bool): The condition to evaluate for the suggestion; the suggestion is associated with this condition.
            message (str): A descriptive message explaining the suggestion or guidance to prefer.
        """
        pass

    def Assert(condition: bool, message: str) -> None:  # noqa: N802
        """
        Enforces a hard routing constraint by asserting that a condition holds.

        Raises an AssertionError with the provided message if `condition` is False; does nothing when `condition` is True.

        Parameters:
            condition (bool): The condition that must be true.
            message (str): The message to include in the AssertionError when the condition is false.

        Raises:
            AssertionError: If `condition` is False.
        """
        pass

else:
    Suggest = getattr(dspy, "Suggest", None)
    Assert = getattr(dspy, "Assert", None)

    if Suggest is None:
        logger.debug(
            "dspy.Suggest is not available; soft assertions will be skipped. "
            "Constraints should be learned via GEPA optimization instead."
        )

        def Suggest(condition: bool, message: str) -> None:  # noqa: N802
            """
            Record a soft suggestion that a routing condition should hold to guide decision making without enforcing failure.

            Parameters:
                condition (bool): The boolean condition being suggested to hold.
                message (str): Human-readable explanation or guidance applied if the suggestion is not met.
            """
            pass

    if Assert is None:
        logger.debug(
            "dspy.Assert is not available; hard assertions will be skipped. "
            "Use typed signatures for validation instead."
        )

        def Assert(condition: bool, message: str) -> None:  # noqa: N802
            """
            No-op placeholder for DSPy-style hard assertions used when the real `Assert` is unavailable.

            This function accepts an assertion `condition` and a `message` describing the failure; in a full DSPy runtime the assertion would raise or trigger backtracking with `message`, but this shim performs no action so it never raises.
            """
            pass


# --- Agent Assignment Assertions ---


def validate_agent_exists(
    assigned_agents: list[str] | tuple[str, ...],
    available_agents: list[str] | tuple[str, ...],
) -> bool:
    """
    Check whether every assigned agent name appears in the available agents (case-insensitive).

    Parameters:
        assigned_agents (list[str] | tuple[str, ...]): Agent names assigned to the task.
        available_agents (list[str] | tuple[str, ...]): Agent names available in the team.

    Returns:
        bool: `True` if every name in `assigned_agents` matches an entry in `available_agents` when compared case-insensitively, `False` otherwise.
    """
    available_set = {a.lower() for a in available_agents}
    return all(agent.lower() in available_set for agent in assigned_agents)


def assert_valid_agents(
    assigned_agents: list[str] | tuple[str, ...],
    available_agents: list[str] | tuple[str, ...],
) -> None:
    """
    Enforces that every agent in `assigned_agents` exists among `available_agents` using case-insensitive name comparison.

    Parameters:
        assigned_agents (list[str] | tuple[str, ...]): Agent names assigned to the routing decision.
        available_agents (list[str] | tuple[str, ...]): Agent names available in the team; comparison is case-insensitive.
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
    """
    Emit a soft routing suggestion that all assigned agents are present in the available agent list.

    When the check fails, a Suggest is issued with a message listing the provided available agents.
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
    """
    Check whether every assigned tool is present in the available tool set (case-insensitive).

    Parameters:
        assigned_tools (list[str] | tuple[str, ...]): Tool names assigned to the task.
        available_tools (list[str] | tuple[str, ...]): Tool names that are available.

    Returns:
        True if all assigned tools are present in available_tools, False otherwise.
    """
    available_set = {t.lower() for t in available_tools}
    return all(tool.lower() in available_set for tool in assigned_tools)


def assert_valid_tools(
    assigned_tools: list[str] | tuple[str, ...],
    available_tools: list[str] | tuple[str, ...],
) -> None:
    """
    Enforce that every assigned tool is present in the available tools (comparison is case-insensitive); triggers a hard assertion if any assigned tool is missing.

    Parameters:
        assigned_tools (list[str] | tuple[str, ...]): Tools requested in the routing decision.
        available_tools (list[str] | tuple[str, ...]): Tools available to assign; compared case-insensitively against `assigned_tools`.
    """
    Assert(
        validate_tool_assignment(assigned_tools, available_tools),
        f"All assigned tools must exist. "
        f"Assigned: {list(assigned_tools)}, Available: {list(available_tools)}",
    )


def suggest_valid_tools(
    assigned_tools: list[str] | tuple[str, ...],
    available_tools: list[str] | tuple[str, ...],
) -> None:
    """
    Suggest that each assigned tool is present in the available tools list.

    Emits a soft routing suggestion that favors assignments where every name in `assigned_tools`
    (case-sensitive) appears in `available_tools`. The suggestion message includes the
    provided `available_tools` for context.

    Parameters:
        assigned_tools (list[str] | tuple[str, ...]): Tools proposed for assignment.
        available_tools (list[str] | tuple[str, ...]): Tools actually available to route to.
    """
    Suggest(
        validate_tool_assignment(assigned_tools, available_tools),
        f"Assigned tools should exist. Available tools: {list(available_tools)}",
    )


# --- Execution Mode Assertions ---


def validate_mode_agent_match(
    mode: ExecutionMode | str,
    agent_count: int,
) -> bool:
    """
    Check whether an execution mode is compatible with the number of assigned agents.

    Parameters:
        mode (ExecutionMode | str): Execution mode or its raw string representation.
        agent_count (int): Number of assigned agents.

    Returns:
        bool: `true` if the mode is compatible with agent_count, `false` otherwise.
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
    """
    Ensure the execution mode is compatible with the number of assigned agents.

    Parameters:
        mode (ExecutionMode | str): Execution mode to validate; may be an ExecutionMode enum or its string form.
        agent_count (int): Number of agents assigned to the task.

    Notes:
        - DELEGATED requires exactly 1 agent.
        - GROUP_CHAT and DISCUSSION require at least 2 agents.
        - Violations trigger a hard routing assertion.
    """
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
    """
    Suggest a soft constraint that the execution mode aligns with the number of assigned agents.

    Emits a suggestion if the provided mode is inconsistent with the agent count (for example, DELEGATED requires exactly 1 agent, GROUP_CHAT/DISCUSSION require at least 2).

    Parameters:
        mode (ExecutionMode | str): The execution mode to validate; may be an ExecutionMode enum or its string name.
        agent_count (int): The number of agents assigned to the task.
    """
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
    """
    Classify a task description into a primary task type.

    Parameters:
        task (str): Task description text to classify.

    Returns:
        str: One of "research", "coding", "analysis", "writing", or "general" indicating the detected task type.
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
    """
    Suggest routing adjustments based on the detected task type.

    Emits soft suggestions about recommended tools and agent roles for tasks classified as
    research, coding, analysis, or writing (for example, recommending a search tool and a
    Researcher for research tasks, or a code execution tool and a Coder for coding tasks).

    Parameters:
        task (str): The task description to classify.
        assigned_agents (list[str] | tuple[str, ...]): Agent names currently assigned to the task.
        tool_requirements (list[str] | tuple[str, ...]): Tool names currently required or planned for the task.
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
    """
    Validate and refine a routing decision by applying hard assertions and soft suggestions.

    Applies a hard Assert that at least one agent is assigned, suggests consistency between execution mode and agent count, and adds task-type and legacy suggestions about required tools and preferred modes (e.g., search tool for research tasks, code interpreter for calculation tasks, multi-agent tasks not delegated, single-agent tasks preferably delegated).

    Parameters:
        decision (RoutingDecision): The routing decision to validate and refine.
        task (str): The original task description used to infer task type and tool requirements.
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
    """
    Run comprehensive routing validation and suggestions using full context.

    Performs hard assertions and soft suggestions for a routing decision and task; if a dict is provided, it is converted to a RoutingDecision before validation. When available_agents or available_tools are provided, additional soft suggestions are applied to guide agent and tool selection.

    Parameters:
        decision (RoutingDecision | dict[str, Any]): RoutingDecision instance or a mapping convertible via RoutingDecision.from_mapping.
        task (str): The original task description used for task-type based checks.
        available_agents (list[str] | None): Optional list of available agent names to validate against; when supplied, agent existence suggestions are emitted.
        available_tools (list[str] | None): Optional list of available tool names to validate against; when supplied and the decision includes tool requirements, tool existence suggestions are emitted.
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
    """
    Wraps a DSPy routing module with runtime assertions that enforce routing constraints when possible.

    When DSPy's `assert_transform_module` is available this decorator applies the transform so assertions and suggestions
    defined in the module run during execution; if the transform is unavailable the original function is executed directly.
    The `_max_backtracks` parameter is reserved for future use and currently has no effect.

    Parameters:
        _max_backtracks (int): Reserved maximum number of assertion retries; currently unused.

    Returns:
        function: A decorator that wraps the target function with DSPy assertion behavior when available.
    """

    # Note: _max_backtracks is reserved for future use when dspy.assert_transform_module
    # supports configurable backtracking limits
    def decorator(func):
        """
        Create a decorator that applies DSPy's assertion transform to a function at call time when available.

        Parameters:
            func (callable): The function to decorate.

        Returns:
            callable: A wrapper that, when called, invokes `func` wrapped with `dspy.assert_transform_module` if present; otherwise invokes `func` directly.
        """

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
