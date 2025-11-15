"""Quality criteria generation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from agent_framework import ChatAgent

from ...utils.logger import setup_logger

logger = setup_logger(__name__)


async def get_quality_criteria(
    task: str,
    agents: dict[str, Any],
    call_judge_fn: Callable[[ChatAgent, str], Awaitable[Any]],
) -> str:
    """Generate task-specific quality criteria using Judge agent.

    Args:
        task: The task to generate criteria for
        agents: Dictionary of available agents
        call_judge_fn: Function to call judge agent with reasoning

    Returns:
        Task-specific quality criteria string
    """
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
