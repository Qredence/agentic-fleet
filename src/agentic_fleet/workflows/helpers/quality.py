"""Quality assessment helpers.

This module provides utilities for quality evaluation, judge prompting,
response parsing, and result refinement.
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Awaitable, Callable
from typing import Any

from agent_framework._agents import ChatAgent

from ...utils.logger import setup_logger

logger = setup_logger(__name__)


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
