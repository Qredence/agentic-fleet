"""Quality assessment logic."""

from __future__ import annotations

import contextlib
import re
from collections.abc import Awaitable, Callable
from typing import Any

from agent_framework import ChatAgent

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
    # The reasoning effort should be included in the request body if extra_body is supported
    return judge_agent.run(prompt)


async def assess_quality(
    task: str,
    result: str,
    compiled_supervisor: Any,
    call_with_retry: Callable[..., Awaitable[Any] | Any],
    normalize_quality: Callable[[Any, str, str], dict[str, Any]],
    fallback_quality: Callable[[str, str], dict[str, Any]],
    record_status: Callable[[str, str], None],
) -> dict[str, Any]:
    """Assess final output quality."""
    used_fallback = False
    try:
        raw_quality = await call_with_retry(
            compiled_supervisor.assess_quality,
            requirements=task,
            results=result,
        )
        quality = normalize_quality(raw_quality, task, result)
    except Exception as exc:
        logger.exception("DSPy quality assessment failed; using fallback: %s", exc)
        quality = fallback_quality(task, result)
        used_fallback = True

    record_status("quality", "fallback" if used_fallback else "success")
    return quality


async def judge_phase(
    task: str,
    result: str,
    agents: dict[str, Any],
    config: Any,
    get_quality_criteria_fn: Callable[[str], Awaitable[str]],
    parse_judge_response_fn: Callable[
        [str, str, str, str, Any, Callable[[str], str | None]], dict[str, Any]
    ],
    determine_refinement_agent_fn: Callable[[str], str | None],
    record_status: Callable[[str, str], None],
) -> dict[str, Any]:
    """Judge evaluation phase using Judge ChatAgent from agent-framework."""
    if not config.enable_judge:
        logger.debug("Judge evaluation disabled, skipping")
        return {
            "score": 10.0,
            "missing_elements": "",
            "refinement_needed": "no",
            "refinement_agent": None,
            "required_improvements": "",
        }

    if "Judge" not in agents:
        logger.warning("Judge agent not available, skipping judge phase")
        return {
            "score": 10.0,
            "missing_elements": "",
            "refinement_needed": "no",
            "refinement_agent": None,
            "required_improvements": "",
        }

    try:
        judge_agent = agents["Judge"]

        # Generate task-specific quality criteria dynamically
        quality_criteria = await get_quality_criteria_fn(task)
        logger.debug(f"Generated quality criteria for task: {quality_criteria[:200]}...")

        # Build evaluation prompt
        evaluation_prompt = f"""Evaluate the following response based on the task-specific quality criteria:

Task: {task}

Quality Criteria:
{quality_criteria}

Response to Evaluate:
{result}

Please provide your evaluation in the specified format:
Score: X/10 (where X reflects how well the response meets the task-specific criteria)
Missing elements: List what's missing based on the criteria above (comma-separated)
Refinement agent: Agent name that should handle improvements (Researcher, Analyst, or Writer)
Refinement needed: yes/no
Required improvements: Specific instructions for the refinement agent"""

        # Use agent-framework's agent.run() for judge evaluation with reasoning effort
        judge_response = await call_judge_with_reasoning(
            judge_agent, evaluation_prompt, config.judge_reasoning_effort
        )
        judge_text = str(judge_response) if judge_response else ""

        # Parse judge's response to extract structured evaluation
        judge_eval = parse_judge_response_fn(
            judge_text, task, result, quality_criteria, config, determine_refinement_agent_fn
        )

        record_status("judge", "success")
        logger.info(
            f"Judge evaluation: score={judge_eval['score']}/10, refinement_needed={
                judge_eval['refinement_needed']
            }"
        )
        return judge_eval

    except Exception as exc:
        logger.exception("Judge evaluation failed: %s", exc)
        record_status("judge", "failed")
        # Return default evaluation that doesn't trigger refinement
        return {
            "score": 10.0,
            "missing_elements": "",
            "refinement_needed": "no",
            "refinement_agent": None,
            "required_improvements": "",
        }


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
