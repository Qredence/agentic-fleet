"""Agent factory for creating workflow agents."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from agent_framework import ChatAgent

from ...agents.coordinator import AgentFactory
from ...tools import BrowserTool, HostedCodeInterpreterAdapter, TavilyMCPTool
from ...utils.logger import setup_logger
from .validation import validate_tool

logger = setup_logger(__name__)


def create_agents(
    config: Any,
    openai_client: Any,
    tool_registry: Any,
    create_client_fn: Callable[[bool], Any] | None = None,
) -> dict[str, ChatAgent]:
    """Create specialized agents for the workflow using AgentFactory.

    Args:
        config: WorkflowConfig instance
        openai_client: Shared OpenAI async client
        tool_registry: ToolRegistry instance
        create_client_fn: Optional function to create OpenAI client (legacy support)

    Returns:
        Dictionary mapping agent names to ChatAgent instances
    """
    # Ensure OpenAI client is available
    if openai_client is None:
        if create_client_fn:
            openai_client = create_client_fn(config.enable_completion_storage)
            logger.warning("OpenAI client created lazily - should be created in initialize()")
        else:
            raise ValueError("openai_client must be provided or create_client_fn must be set")

    # Initialize AgentFactory with the shared client
    factory = AgentFactory(tool_registry=tool_registry, openai_client=openai_client)

    agents = {}

    # --- Researcher Setup ---
    researcher_tool_names = []

    # Tavily
    try:
        # Check environment or config for Tavily key
        if os.getenv("TAVILY_API_KEY"):
            tavily_tool = TavilyMCPTool()
            if validate_tool(tavily_tool):
                # Register tool if not already in registry
                if not tool_registry.get_tool(tavily_tool.name):
                    tool_registry.register_tool(tavily_tool)
                researcher_tool_names.append(tavily_tool.name)
                logger.info("TavilyMCPTool enabled for Researcher")
        else:
            logger.warning("TAVILY_API_KEY not set - Researcher will operate without Tavily search")
    except Exception as e:
        logger.warning(f"Failed to initialize TavilyMCPTool: {e}")

    # Browser
    try:
        browser_tool = BrowserTool(headless=True)
        if validate_tool(browser_tool):
            if not tool_registry.get_tool(browser_tool.name):
                tool_registry.register_tool(browser_tool)
            researcher_tool_names.append(browser_tool.name)
            logger.info("BrowserTool enabled for Researcher")
    except ImportError:
        logger.warning("BrowserTool unavailable (playwright not installed)")
    except Exception as e:
        logger.warning(f"Failed to initialize BrowserTool: {e}")

    agents["Researcher"] = factory.create_agent(
        "Researcher",
        {
            "model": (config.agent_models or {}).get("researcher", config.dspy_model),
            "temperature": (config.agent_temperatures or {}).get("researcher"),
            "description": "Information gathering and web research specialist",
            "instructions": (
                "You are a research specialist. Your job is to find accurate, up-to-date information. "
                "CRITICAL RULES:\n"
                "1. For ANY query mentioning a year (2024, 2025, etc.) or asking about 'current', 'latest', 'recent', or 'who won' - "
                "you MUST IMMEDIATELY use the tavily_search tool. DO NOT answer from memory.\n"
                "2. NEVER rely on training data for time-sensitive information - it is outdated.\n"
                "3. When you see a question about elections, current events, recent news, or anything with a date, "
                "your FIRST action must be to call tavily_search with an appropriate query.\n"
                "4. Only after getting search results should you provide an answer.\n"
                "5. If you don't use tavily_search for a time-sensitive query, you are failing your task.\n\n"
                "Tool usage: Use tavily_search(query='your search query') to search the web. "
                "Use browser tool for direct website access when needed."
            ),
            "tools": researcher_tool_names,
            "enable_dspy": True,
            "reasoning_strategy": "react",
        },
    )

    # --- Analyst Setup ---
    analyst_tool_names = []
    try:
        analyst_tool = HostedCodeInterpreterAdapter()
        if validate_tool(analyst_tool):
            if not tool_registry.get_tool(analyst_tool.name):
                tool_registry.register_tool(analyst_tool)
            analyst_tool_names.append(analyst_tool.name)
    except Exception as e:
        logger.warning(f"Failed to initialize Analyst tool: {e}")

    agents["Analyst"] = factory.create_agent(
        "Analyst",
        {
            "model": (config.agent_models or {}).get("analyst", config.dspy_model),
            "temperature": (config.agent_temperatures or {}).get("analyst"),
            "description": "Data analysis and computation specialist",
            "instructions": "Perform detailed analysis with code and visualizations",
            "tools": analyst_tool_names,
            "enable_dspy": True,
            "reasoning_strategy": "program_of_thought",
        },
    )

    # --- Writer Setup ---
    agents["Writer"] = factory.create_agent(
        "Writer",
        {
            "model": (config.agent_models or {}).get("writer", config.dspy_model),
            "temperature": (config.agent_temperatures or {}).get("writer"),
            "description": "Content creation and report writing specialist",
            "instructions": "Create clear, well-structured documents",
            "enable_dspy": False,
        },
    )

    # --- Judge Setup ---
    judge_instructions = """You are a quality judge that evaluates responses for completeness and accuracy.

Your role has two phases:

1. **Criteria Generation Phase**: When asked to generate quality criteria for a task, analyze the task type and create appropriate criteria:
   - Math/calculation tasks: Focus on accuracy, correctness, step-by-step explanation
   - Research tasks: Focus on citations, dates, authoritative sources, factual accuracy
   - Writing tasks: Focus on clarity, structure, completeness, coherence
   - Factual questions: Focus on accuracy, sources, verification
   - Simple questions (like "2+2"): Focus on correctness and clarity (DO NOT require citations for basic facts)

2. **Evaluation Phase**: When evaluating a response, use the provided task-specific criteria to assess:
   - How well the response meets each criterion
   - What's missing if the response is incomplete
   - Which agent should handle refinement (Researcher for citations/sources, Analyst for calculations/data, Writer for clarity/structure)
   - Specific improvement instructions

Always adapt your evaluation to the task type - don't require citations for simple math problems, and don't require calculations for research questions.

Output your evaluation in this format:
Score: X/10 (where X reflects how well the response meets the task-specific criteria)
Missing elements: List what's missing based on the criteria (comma-separated)
Refinement agent: Agent name that should handle improvements (Researcher, Analyst, or Writer)
Refinement needed: yes/no
Required improvements: Specific instructions for the refinement agent"""

    agents["Judge"] = factory.create_agent(
        "Judge",
        {
            "model": config.judge_model or "gpt-5",
            "description": "Quality evaluation specialist with dynamic task-aware criteria assessment",
            "instructions": judge_instructions,
            "reasoning": {"effort": config.judge_reasoning_effort or "medium"},
            "enable_dspy": False,
        },
    )

    # --- Reviewer Setup ---
    agents["Reviewer"] = factory.create_agent(
        "Reviewer",
        {
            "model": (config.agent_models or {}).get("reviewer", config.dspy_model),
            "description": "Quality assurance and validation specialist",
            "instructions": "Ensure accuracy, completeness, and quality",
            "enable_dspy": False,
        },
    )

    return agents
