"""Agent factory for creating workflow agents."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

from ...tools import BrowserTool, HostedCodeInterpreterAdapter, TavilyMCPTool
from ...utils.logger import setup_logger
from .validation import validate_tool

logger = setup_logger(__name__)


def create_agent(
    name: str,
    description: str,
    instructions: str,
    config: Any,
    openai_client: Any,
    tool_registry: Any,
    create_client_fn: Callable[[bool], Any] | None = None,
    tools: Any | None = None,
    model_override: str | None = None,
    reasoning_effort: str | None = None,
) -> ChatAgent:
    """Factory method for creating agents.

    Args:
        name: Agent name
        description: Agent description
        instructions: Agent instructions
        config: WorkflowConfig instance
        openai_client: Shared OpenAI async client
        tool_registry: ToolRegistry instance
        tools: Optional tool instance or list of tools
        model_override: Optional model ID override
        reasoning_effort: Optional reasoning effort for Judge agent

    Returns:
        Configured ChatAgent instance
    """
    # Use shared OpenAI client (should be provided by caller)
    if openai_client is None:
        if create_client_fn:
            openai_client = create_client_fn(config.enable_completion_storage)
            logger.warning("OpenAI client created lazily - should be created in initialize()")
        else:
            raise ValueError("openai_client must be provided or create_client_fn must be set")

    agent_models = config.agent_models or {}
    model_id = model_override or agent_models.get(name.lower(), config.dspy_model)

    # Get agent-specific temperature if configured
    agent_temperatures = config.agent_temperatures or {}
    temperature = agent_temperatures.get(name.lower())

    # Create chat client with optional temperature and reasoning effort
    async_client = openai_client

    chat_client_kwargs: dict[str, Any] = {
        "model_id": model_id,
        "async_client": async_client,
    }

    if temperature is not None:
        logger.debug(f"Agent {name} temperature configured: {temperature}")

    # Validate and filter tools before passing to ChatAgent
    validated_tools = None
    if tools is not None:
        if isinstance(tools, list):
            # Validate each tool in the list
            validated_tools = [tool for tool in tools if validate_tool(tool)]
            invalid_count = len(tools) - len(validated_tools)
            if invalid_count > 0:
                logger.warning(
                    f"Filtered out {invalid_count} invalid tool(s) for agent {name}. "
                    f"Valid tools: {len(validated_tools)}"
                )
            # Convert to single tool if only one, or None if empty
            if len(validated_tools) == 0:
                validated_tools = None
            elif len(validated_tools) == 1:
                validated_tools = validated_tools[0]
        else:
            # Single tool
            if validate_tool(tools):
                validated_tools = tools
            else:
                logger.warning(f"Invalid tool for agent {name}, skipping tool assignment")
                validated_tools = None

    # Create the chat client
    chat_client = OpenAIChatClient(**chat_client_kwargs)

    # For Judge agent with reasoning effort, set extra_body after creation
    if reasoning_effort is not None and name == "Judge":
        try:
            if hasattr(chat_client, "extra_body"):
                chat_client.extra_body = {  # type: ignore[attr-defined]
                    "reasoning": {"effort": reasoning_effort}
                }
                logger.debug(
                    f"Judge agent configured with reasoning effort via extra_body: {reasoning_effort}"
                )
            else:
                chat_client._reasoning_effort = reasoning_effort  # type: ignore[attr-defined]
                logger.debug(
                    f"Judge agent reasoning effort stored: {reasoning_effort} (will be applied in request)"
                )
        except Exception as e:
            logger.warning(f"Could not set reasoning effort on chat client: {e}")

    return ChatAgent(
        name=name,
        description=description,
        instructions=instructions,
        chat_client=chat_client,
        tools=validated_tools,
    )


def create_agents(
    config: Any,
    openai_client: Any,
    tool_registry: Any,
    create_client_fn: Callable[[bool], Any] | None = None,
) -> dict[str, ChatAgent]:
    """Create specialized agents for the workflow."""

    agents = {}

    # Researcher with Tavily (optional) and BrowserTool
    researcher_tools = []
    tavily_mcp_tool = None
    try:
        # Add Tavily if available (via MCP)
        if os.getenv("TAVILY_API_KEY"):
            tavily_mcp_tool = TavilyMCPTool()  # type: ignore[abstract]
            researcher_tools.append(tavily_mcp_tool)
            logger.info("TavilyMCPTool enabled for Researcher")
        else:
            logger.warning("TAVILY_API_KEY not set - Researcher will operate without Tavily search")
    except Exception as e:
        logger.warning(f"Failed to initialize TavilyMCPTool: {e}")

    # Add BrowserTool for real-time web browsing
    try:
        browser_tool = BrowserTool(headless=True)
        researcher_tools.append(browser_tool)
        logger.info("BrowserTool enabled for Researcher")
    except ImportError as e:
        logger.warning(
            f"BrowserTool not available (playwright not installed): {e}. "
            "Install with: uv pip install playwright && playwright install chromium"
        )
    except Exception as e:
        logger.warning(f"Failed to initialize BrowserTool: {e}")

    # Convert to single tool or list as needed by agent-framework
    if len(researcher_tools) == 1:
        tools_for_researcher = researcher_tools[0]
        logger.debug(f"Researcher agent: 1 tool ({type(tools_for_researcher).__name__})")
    elif researcher_tools:
        tools_for_researcher = researcher_tools
        logger.debug(f"Researcher agent: {len(researcher_tools)} tools")
    else:
        tools_for_researcher = None
        logger.debug("Researcher agent: no tools")

    agents["Researcher"] = create_agent(
        name="Researcher",
        description="Information gathering and web research specialist",
        instructions=(
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
        config=config,
        openai_client=openai_client,
        tool_registry=tool_registry,
        create_client_fn=create_client_fn,
        tools=tools_for_researcher,
    )

    # Register MCP tool directly if it was created
    if tavily_mcp_tool is not None:
        try:
            if validate_tool(tavily_mcp_tool):
                tool_registry.register_tool_by_agent("Researcher", tavily_mcp_tool)
                logger.info(
                    f"Registered MCP tool for Researcher: {tavily_mcp_tool.name} "
                    f"(type: {type(tavily_mcp_tool).__name__})"
                )
        except Exception as e:
            logger.warning(f"Failed to register MCP tool for Researcher: {e}", exc_info=True)

    # Analyst with HostedCodeInterpreterAdapter (SerializationMixin-compatible)
    analyst_tool = HostedCodeInterpreterAdapter()

    agents["Analyst"] = create_agent(
        name="Analyst",
        description="Data analysis and computation specialist",
        instructions="Perform detailed analysis with code and visualizations",
        config=config,
        openai_client=openai_client,
        tool_registry=tool_registry,
        create_client_fn=create_client_fn,
        tools=analyst_tool,
    )

    agents["Writer"] = create_agent(
        name="Writer",
        description="Content creation and report writing specialist",
        instructions="Create clear, well-structured documents",
        config=config,
        openai_client=openai_client,
        tool_registry=tool_registry,
        create_client_fn=create_client_fn,
    )

    # Judge agent for detailed quality evaluation
    judge_model = config.judge_model or "gpt-5"
    judge_reasoning_effort = config.judge_reasoning_effort or "medium"

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

    agents["Judge"] = create_agent(
        name="Judge",
        description="Quality evaluation specialist with dynamic task-aware criteria assessment",
        instructions=judge_instructions,
        config=config,
        openai_client=openai_client,
        tool_registry=tool_registry,
        create_client_fn=create_client_fn,
        model_override=judge_model,
        reasoning_effort=judge_reasoning_effort,
    )

    # Reviewer for backward compatibility
    agents["Reviewer"] = create_agent(
        name="Reviewer",
        description="Quality assurance and validation specialist",
        instructions="Ensure accuracy, completeness, and quality",
        config=config,
        openai_client=openai_client,
        tool_registry=tool_registry,
        create_client_fn=create_client_fn,
    )

    return agents
