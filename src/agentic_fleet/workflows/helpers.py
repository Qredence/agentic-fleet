"""Helper functions for routing, quality assessment, and workflow utilities.

Consolidated from routing/, quality/ submodules, task_utils, and workflow utilities.
"""

from __future__ import annotations

import contextlib
import os
import re
from collections.abc import Awaitable, Callable
from typing import Any

import openai
from agent_framework._agents import ChatAgent

from ..utils.logger import setup_logger
from ..utils.models import ExecutionMode, RoutingDecision, ensure_routing_decision

logger = setup_logger(__name__)


# --- Task Classification Helpers ---


def is_simple_task(task: str) -> bool:
    """Identify simple tasks that can be answered directly without multi-agent routing.

    This function detects tasks that should bypass the full orchestration pipeline:
    - Greetings and heartbeats
    - Simple factual questions
    - Math/calculations
    - Direct knowledge questions

    Args:
        task: The task string to classify

    Returns:
        True if the task is simple enough to bypass routing, False otherwise
    """
    task_lower = task.strip().lower()
    word_count = len(task.split())

    # Keywords that imply real-time data or complex research needs
    complex_keywords = [
        "news",
        "latest",
        "current",
        "election",
        "price",
        "stock",
        "weather",
        "who won",
        "mayor",
        "governor",
        "president",
        "compare and contrast",
        "analyze in detail",
        "create a plan",
        "step by step guide",
        "comprehensive",
        "research",
        "investigate",
    ]

    # Patterns that require multi-step workflows
    complex_patterns = [
        r"create\s+(a\s+)?(detailed|full|comprehensive)",
        r"write\s+(a\s+)?(report|essay|article|document)",
        r"plan\s+(a\s+|my\s+)?(trip|project|event|wedding)",
        r"help\s+me\s+(plan|design|build|create)",
        r"include\s+.*(activities|restaurants|hotels|examples)",
    ]

    # Heartbeat / greeting style tasks
    trivial_keywords = [
        "ping",
        "hello",
        "hi",
        "hey",
        "test",
        "are you there",
        "you there",
        "you awake",
        "good morning",
        "good evening",
        "thanks",
        "thank you",
    ]

    # Keywords/patterns that imply a simple direct response
    simple_keywords = [
        "define",
        "calculate",
        "solve",
        "meaning of",
        "what is",
        "what are",
        "who is",
        "who are",
        "how many",
        "how much",
        "when was",
        "when did",
        "where is",
        "where are",
        "why is",
        "why do",
        "explain",
        "describe",
        "list",
        "name",
    ]

    # Math patterns (arithmetic expressions)
    math_patterns = [
        r"^\d+\s*[\+\-\*\/\^]\s*\d+",  # "7+7", "2*3", etc.
        r"^\d+\s*\+\s*\d+",  # Addition
        r"what\s+is\s+\d+\s*[\+\-\*\/]",  # "what is 2+2"
        r"calculate\s+\d+",
        r"solve\s+\d+",
    ]

    # Check for time-sensitive content (years like 2024, 2025)
    is_time_sensitive = bool(re.search(r"20[2-9][0-9]", task))

    # Check complex patterns first
    has_complex_keyword = any(
        re.search(r"\b" + re.escape(k) + r"\b", task_lower) for k in complex_keywords
    )
    has_complex_pattern = any(re.search(p, task_lower) for p in complex_patterns)

    # If complex indicators found, not simple
    if has_complex_keyword or has_complex_pattern:
        return False

    # Check for trivial/greeting tasks
    has_trivial_keyword = any(
        re.search(r"\b" + re.escape(k) + r"\b", task_lower) for k in trivial_keywords
    )
    if has_trivial_keyword:
        return True

    # Check for math expressions
    has_math_pattern = any(re.search(p, task_lower) for p in math_patterns)
    if has_math_pattern:
        return True

    # Check for simple question patterns
    has_simple_keyword = any(
        re.search(r"^" + re.escape(k) + r"\b", task_lower) for k in simple_keywords
    )

    # Short tasks (under 15 words) starting with simple keywords are simple
    # unless they're time-sensitive
    if has_simple_keyword and word_count <= 15 and not is_time_sensitive:
        return True

    # Very short tasks (under 8 words) without complex keywords are likely simple
    return word_count <= 8 and not is_time_sensitive


# --- Workflow Utility Functions ---


def synthesize_results(results: list[Any]) -> str:
    """Combine parallel results into a single string.

    Args:
        results: List of results from parallel execution

    Returns:
        Combined results as a single string
    """
    return "\n\n".join([str(r) for r in results])


def extract_artifacts(result: Any) -> dict[str, Any]:
    """Extract artifacts from agent result.

    Parses agent output to identify structured data, files, or
    other artifacts produced during execution. Currently returns
    a summary placeholder.

    Args:
        result: The raw result from an agent execution.

    Returns:
        Dictionary mapping artifact names to their values.
        Currently contains a 'result_summary' key with truncated output.

    Example:
        >>> artifacts = extract_artifacts("Long agent response...")
        >>> print(artifacts["result_summary"])
        'Long agent response...'
    """
    # Placeholder - could be enhanced to extract structured data
    return {"result_summary": str(result)[:200]}


def estimate_remaining_work(original_task: str, work_done: str) -> str:
    """Estimate what work remains based on original task and progress.

    Args:
        original_task: The original task description
        work_done: Description of work completed so far

    Returns:
        Description of remaining work
    """
    # Simple heuristic - in practice, could use DSPy for this
    return f"Continue working on: {original_task}. Already completed: {work_done[:100]}..."


def derive_objectives(remaining_work: str) -> list[str]:
    """Derive specific objectives from remaining work description.

    Args:
        remaining_work: Description of remaining work

    Returns:
        List of specific objectives
    """
    # Simple extraction - could use NLP or DSPy
    objectives = [remaining_work]
    return objectives


def create_openai_client_with_store(
    enable_storage: bool = False,
    reasoning_effort: str | None = None,
) -> openai.AsyncOpenAI:
    """Create AsyncOpenAI client configured to optionally store completions and set reasoning effort.

    Args:
        enable_storage: Whether to enable completion storage
        reasoning_effort: Optional reasoning effort level ("minimal", "medium", "maximal") for GPT-5 models

    Returns:
        AsyncOpenAI client with default_query set to include store=true if enabled
    """
    kwargs: dict[str, Any] = {}

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        kwargs["api_key"] = api_key

    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        normalized = base_url.strip()
        if "://" not in normalized:
            normalized = "https://" + normalized.lstrip("/")
            logger.warning(
                "OPENAI_BASE_URL was missing scheme; normalized to %s",
                normalized,
            )
        kwargs["base_url"] = normalized

    default_query: dict[str, Any] = {}
    if enable_storage:
        default_query["store"] = "true"

    # Reasoning effort is passed in the request body, not query params
    # We'll need to handle this via extra_body in the actual request
    # For now, we store it as a client attribute for later use
    client = openai.AsyncOpenAI(**kwargs)
    if reasoning_effort is not None:
        # Store reasoning effort as client attribute for use in requests
        client._reasoning_effort = reasoning_effort  # type: ignore[attr-defined]

    if default_query:
        # Note: default_query might not support nested dicts for reasoning
        # Reasoning effort needs to be in request body, not query params
        pass

    return client


# --- Routing Helpers ---


def normalize_routing_decision(
    routing: RoutingDecision | dict[str, Any], task: str
) -> RoutingDecision:
    """Ensure routing output has valid agents, mode, and subtasks."""
    # Convert dict to RoutingDecision if needed
    if isinstance(routing, dict):
        routing = ensure_routing_decision(routing)

    # Validate and normalize
    if not routing.assigned_to:
        # Fallback: assign to Researcher for research tasks
        routing = RoutingDecision(
            task=task,
            assigned_to=("Researcher",),
            mode=ExecutionMode.DELEGATED,
            subtasks=(),
            confidence=routing.confidence,
        )

    # Ensure mode is valid
    if routing.mode not in (
        ExecutionMode.DELEGATED,
        ExecutionMode.SEQUENTIAL,
        ExecutionMode.PARALLEL,
    ):
        routing = RoutingDecision(
            task=routing.task,
            assigned_to=routing.assigned_to,
            mode=ExecutionMode.DELEGATED,
            subtasks=routing.subtasks,
            confidence=routing.confidence,
        )

    # Normalize latency-conscious defaults:
    # - Delegated with multiple agents ⇒ parallel fan-out.
    # - Parallel with insufficient subtasks ⇒ normalize subtasks.
    # - Parallel with single agent ⇒ back to delegated.
    if routing.mode is ExecutionMode.DELEGATED and len(routing.assigned_to) > 1:
        routing = RoutingDecision(
            task=routing.task,
            assigned_to=routing.assigned_to,
            mode=ExecutionMode.PARALLEL,
            subtasks=tuple(
                prepare_subtasks(
                    list(routing.assigned_to),
                    list(routing.subtasks) if routing.subtasks is not None else None,
                    task,
                )
            ),
            confidence=routing.confidence,
            tool_requirements=routing.tool_requirements,
        )

    elif routing.mode is ExecutionMode.PARALLEL:
        if len(routing.assigned_to) <= 1:
            routing = RoutingDecision(
                task=routing.task,
                assigned_to=routing.assigned_to,
                mode=ExecutionMode.DELEGATED,
                subtasks=routing.subtasks,
                confidence=routing.confidence,
                tool_requirements=routing.tool_requirements,
            )
        else:
            routing = RoutingDecision(
                task=routing.task,
                assigned_to=routing.assigned_to,
                mode=ExecutionMode.PARALLEL,
                subtasks=tuple(
                    prepare_subtasks(
                        list(routing.assigned_to),
                        list(routing.subtasks) if routing.subtasks is not None else None,
                        task,
                    )
                ),
                confidence=routing.confidence,
                tool_requirements=routing.tool_requirements,
            )

    return routing


def detect_routing_edge_cases(task: str, routing: RoutingDecision) -> list[str]:
    """Detect edge cases in routing decisions for logging and learning.

    Identifies potential issues or unusual patterns in routing decisions
    that may require attention or could be used for improving future routing.

    Args:
        task: The original task being routed.
        routing: The routing decision to analyze.

    Returns:
        List of detected edge case descriptions. Empty if no issues found.

    Example:
        >>> edge_cases = detect_routing_edge_cases("Find today's news", routing)
        >>> if edge_cases:
        ...     logger.warning(f"Edge cases: {edge_cases}")
    """
    edge_cases = []

    # Check for ambiguous routing
    if routing.confidence is not None and routing.confidence < 0.5:
        edge_cases.append("Low confidence routing decision")

    # Check for mismatched mode and agents
    if routing.mode == ExecutionMode.PARALLEL and len(routing.assigned_to) == 1:
        edge_cases.append("Parallel mode with single agent")

    if routing.mode == ExecutionMode.DELEGATED and len(routing.assigned_to) > 1:
        edge_cases.append("Delegated mode with multiple agents")

    # Check for empty subtasks in parallel mode
    if routing.mode == ExecutionMode.PARALLEL and not routing.subtasks:
        edge_cases.append("Parallel mode without subtasks")

    # Time-sensitive queries should include a web-search tool
    if is_time_sensitive_task(task):
        has_web_tool = bool(
            routing.tool_requirements
            and any(
                t.lower().startswith("tavily") or "search" in t.lower() or "web" in t.lower()
                for t in routing.tool_requirements
            )
        )
        if not has_web_tool:
            edge_cases.append("Time-sensitive task missing web search tool")

    return edge_cases


def prepare_subtasks(
    agents: list[str], subtasks: list[str] | None, fallback_task: str
) -> list[str]:
    """Normalize DSPy-provided subtasks to align with assigned agents.

    Ensures the number of subtasks matches the number of agents by
    either padding with the fallback task or truncating excess subtasks.

    Args:
        agents: List of agent names assigned to the task.
        subtasks: Optional list of subtasks from DSPy routing.
        fallback_task: Task to use when subtasks are missing or insufficient.

    Returns:
        List of subtasks with length equal to number of agents.
    """
    if not agents:
        return []

    normalized: list[str]
    if not subtasks:
        normalized = [fallback_task for _ in agents]
    else:
        normalized = [str(task) for task in subtasks]

    if len(normalized) < len(agents):
        normalized.extend([fallback_task] * (len(agents) - len(normalized)))
    elif len(normalized) > len(agents):
        normalized = normalized[: len(agents)]

    return normalized


def is_time_sensitive_task(task: str) -> bool:
    """Heuristic detection for queries that require fresh, web-sourced data."""

    task_lower = task.lower()
    freshness_keywords = [
        "today",
        "now",
        "current",
        "latest",
        "recent",
        "breaking",
        "this week",
        "this month",
    ]

    if any(keyword in task_lower for keyword in freshness_keywords):
        return True

    # Detect explicit four-digit years 2023+ (signals recency)
    match = re.search(r"\b(20[2-9][0-9])\b", task)
    if match:
        year = int(match.group(1))
        if year >= 2023:
            return True

    return False


# --- Quality Helpers ---


def call_judge_with_reasoning(
    judge_agent: ChatAgent,
    prompt: str,
    reasoning_effort: str = "medium",
) -> Any:
    """Call Judge agent with reasoning effort if configured.

    Uses the Responses API format for reasoning effort: {"reasoning": {"effort": "medium"}}
    This is passed in the request body via extra_body parameter.

    Args:
        judge_agent: The Judge ChatAgent instance
        prompt: The prompt to send to the judge
        reasoning_effort: Reasoning effort level (low, medium, high)

    Returns:
        Response from the judge agent
    """
    # Pass reasoning effort in request body using Responses API format
    # Format: {"reasoning": {"effort": "medium"}}
    if reasoning_effort and hasattr(judge_agent, "chat_client"):
        chat_client = judge_agent.chat_client

        try:
            # Try to set reasoning effort via extra_body (standard OpenAI SDK approach)
            # extra_body is merged into the request body
            if hasattr(chat_client, "extra_body"):
                existing_extra_body = getattr(chat_client, "extra_body", None)
                if not isinstance(existing_extra_body, dict):
                    existing_extra_body = {}
                existing_extra_body["reasoning"] = {"effort": reasoning_effort}
                chat_client.extra_body = existing_extra_body  # type: ignore[attr-defined]
                logger.debug(f"Set reasoning effort via extra_body: {reasoning_effort}")
            elif hasattr(chat_client, "_default_extra_body"):
                default_body = getattr(chat_client, "_default_extra_body", None)
                if not isinstance(default_body, dict):
                    default_body = {}
                default_body["reasoning"] = {"effort": reasoning_effort}
                chat_client._default_extra_body = default_body  # type: ignore[attr-defined]
                logger.debug(f"Set reasoning effort via _default_extra_body: {reasoning_effort}")
            else:
                # Try to set on underlying async_client if available
                async_client = getattr(chat_client, "async_client", None)
                if async_client is not None:
                    chat_client._reasoning_effort = reasoning_effort  # type: ignore[attr-defined]
                    logger.debug(f"Stored reasoning effort on chat client: {reasoning_effort}")
        except Exception as e:
            logger.warning(
                f"Could not set reasoning effort directly: {e}. May need framework support."
            )

    # Call the agent's run method
    return judge_agent.run(prompt)


async def get_quality_criteria(
    task: str,
    agents: dict[str, ChatAgent],
    call_judge_fn: Callable[[ChatAgent, str], Awaitable[Any]],
) -> str:
    """Generate task-specific quality criteria using Judge agent."""
    if "Judge" not in agents:
        # Fallback to generic criteria if Judge not available
        return """Quality Criteria Checklist:
1. Accuracy: Is the information correct and factual?
2. Completeness: Does the response fully address the task?
3. Clarity: Is the response clear and well-structured?
4. Relevance: Is the response relevant to the task?"""

    try:
        judge_agent = agents["Judge"]

        # Ask Judge to generate task-specific criteria
        criteria_prompt = f"""Analyze the following task and generate appropriate quality criteria for evaluating responses to it.

Task: {task}

Generate 3-5 specific quality criteria that are relevant to this task type. Consider:
- For math/calculation tasks: focus on accuracy, correctness, step-by-step explanation
- For research tasks: focus on citations, dates, authoritative sources, factual accuracy
- For writing tasks: focus on clarity, structure, completeness, coherence
- For factual questions: focus on accuracy, sources, verification
- For simple questions: focus on correctness and clarity (don't require citations for basic facts)

Output ONLY the criteria list in this format:
1. Criterion name: Description of what to check
2. Criterion name: Description of what to check
...

Do not include any other text, just the numbered list of criteria."""

        criteria_response = await call_judge_fn(judge_agent, criteria_prompt)
        criteria_text = str(criteria_response) if criteria_response else ""

        # Clean up the response - extract just the criteria list
        if criteria_text.strip():
            # Remove any prefix/suffix text and keep just the numbered list
            lines = criteria_text.strip().split("\n")
            criteria_lines = []
            for line in lines:
                line = line.strip()
                # Keep lines that look like criteria (start with number or bullet)
                if line and (line[0].isdigit() or line.startswith("-") or line.startswith("*")):
                    criteria_lines.append(line)

            if criteria_lines:
                return "Quality Criteria Checklist:\n" + "\n".join(criteria_lines)

        # Fallback if parsing fails
        logger.warning("Failed to parse generated criteria, using fallback")
        return """Quality Criteria Checklist:
1. Accuracy: Is the information correct and factual?
2. Completeness: Does the response fully address the task?
3. Clarity: Is the response clear and well-structured?"""

    except Exception as exc:
        logger.exception(f"Failed to generate dynamic criteria: {exc}, using fallback")
        # Fallback to generic criteria
        return """Quality Criteria Checklist:
1. Accuracy: Is the information correct and factual?
2. Completeness: Does the response fully address the task?
3. Clarity: Is the response clear and well-structured?
4. Relevance: Is the response relevant to the task?"""


def parse_judge_response(
    response: str,
    task: str,
    result: str,
    quality_criteria: str,
    config: Any,
    determine_refinement_agent_fn: Callable[[str], str | None],
) -> dict[str, Any]:
    """Parse judge's response to extract structured evaluation data."""
    # Default values
    score = 10.0
    missing_elements = ""
    refinement_needed = "no"
    refinement_agent = None
    required_improvements = ""

    response_lower = response.lower()

    # Extract score (look for "Score: X/10" or "X/10")
    score_match = re.search(r"score:\s*(\d+(?:\.\d+)?)/10", response_lower, re.IGNORECASE)
    if not score_match:
        score_match = re.search(r"(\d+(?:\.\d+)?)/10", response_lower)
    if score_match:
        with contextlib.suppress(ValueError):
            score = float(score_match.group(1))

    # Extract missing elements
    missing_match = re.search(r"missing elements?:\s*([^\n]+)", response_lower, re.IGNORECASE)
    if missing_match:
        missing_elements = missing_match.group(1).strip()

    # Extract refinement needed
    refinement_match = re.search(r"refinement needed:\s*(yes|no)", response_lower, re.IGNORECASE)
    if refinement_match:
        refinement_needed = refinement_match.group(1).lower()

    # Extract refinement agent
    agent_match = re.search(r"refinement agent:\s*([^\n]+)", response_lower, re.IGNORECASE)
    if agent_match:
        refinement_agent = agent_match.group(1).strip()

    # Extract required improvements
    improvements_match = re.search(
        r"required improvements?:\s*([^\n]+(?:\n[^\n]+)*)", response_lower, re.IGNORECASE
    )
    if improvements_match:
        required_improvements = improvements_match.group(1).strip()

    # If score is below threshold, mark refinement as needed
    if score < config.judge_threshold and refinement_needed == "no":
        refinement_needed = "yes"
        if not refinement_agent:
            # Determine refinement agent based on missing elements
            refinement_agent = determine_refinement_agent_fn(missing_elements)

    return {
        "score": score,
        "missing_elements": missing_elements,
        "refinement_needed": refinement_needed,
        "refinement_agent": refinement_agent,
        "required_improvements": required_improvements,
    }


def build_refinement_task(current_result: str, judge_eval: dict[str, Any]) -> str:
    """Build a refinement task based on judge evaluation."""
    missing_elements = judge_eval.get("missing_elements", "")
    required_improvements = judge_eval.get("required_improvements", "")

    refinement_task = f"""Improve the following response based on the judge's evaluation:

Missing elements: {missing_elements}
Required improvements: {required_improvements}

Current response:
{current_result}

Please enhance the response by addressing the missing elements and required improvements."""

    return refinement_task


async def refine_results(
    results: Any,
    improvements: str,
    agents: dict[str, ChatAgent],
) -> Any:
    """Refine results based on quality assessment."""
    writer = agents.get("Writer")
    if writer is None:
        raise ValueError("Writer agent not found in available agents")
    refinement_task = f"Refine these results based on improvements needed:\n{results}\n\nImprovements: {improvements}"
    try:
        response = await writer.run(refinement_task)
        return str(response) if response is not None else str(results)
    except Exception:
        # Defensive: on any failure, return original results
        return str(results)
