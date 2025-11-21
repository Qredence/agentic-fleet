"""Agent factory for creating ChatAgent instances from YAML configuration."""

from __future__ import annotations

import inspect
import logging
import os
from typing import Any

from agent_framework import BaseAgent, ChatAgent
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv

from agentic_fleet.agents.base import DSPyEnhancedAgent
from agentic_fleet.utils.telemetry import optional_span
from agentic_fleet.utils.tool_registry import ToolRegistry

try:
    from agent_framework.openai import OpenAIResponsesClient as _PreferredOpenAIClient

    _RESPONSES_CLIENT_AVAILABLE = True
except (
    ImportError,
    AttributeError,
):  # pragma: no cover - fallback path depends on installed extras
    _PreferredOpenAIClient = OpenAIChatClient  # type: ignore[assignment]
    _RESPONSES_CLIENT_AVAILABLE = False  # type: ignore[assignment]

load_dotenv(override=True)

logger = logging.getLogger(__name__)
_fallback_warning_emitted = False


def _prepare_kwargs_for_client(client_cls: type, kwargs: dict[str, Any]) -> dict[str, Any]:
    try:
        signature = inspect.signature(client_cls.__init__)
    except (TypeError, ValueError):  # pragma: no cover - defensive guardrail
        return kwargs

    accepts_var_kwargs = any(
        param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()
    )
    if accepts_var_kwargs:
        return kwargs

    allowed_keys = {name for name, parameter in signature.parameters.items() if name != "self"}
    return {key: value for key, value in kwargs.items() if key in allowed_keys}


def _create_openai_client(**kwargs: Any):
    global _fallback_warning_emitted

    client_kwargs = _prepare_kwargs_for_client(_PreferredOpenAIClient, kwargs)
    if not _RESPONSES_CLIENT_AVAILABLE and not _fallback_warning_emitted:
        logger.warning(
            "OpenAIResponsesClient is unavailable; falling back to OpenAIChatClient (Responses API features disabled).",
        )
        _fallback_warning_emitted = True
    return _PreferredOpenAIClient(**client_kwargs)


class AgentFactory:
    """Factory for creating ChatAgent instances from YAML configuration."""

    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        openai_client: Any | None = None,
    ) -> None:
        """Initialize AgentFactory.

        Args:
            tool_registry: Optional tool registry for resolving tool names to instances.
                If None, creates a default registry.
            openai_client: Optional shared OpenAI client (AsyncOpenAI) to reuse.
        """
        self.tool_registry = tool_registry or ToolRegistry()
        self.openai_client = openai_client

        # Check if DSPy enhancement should be enabled globally
        self.enable_dspy = os.getenv("ENABLE_DSPY_AGENTS", "true").lower() == "true"

    def create_agent(
        self,
        name: str,
        agent_config: dict[str, Any],
    ) -> BaseAgent:
        """Create a ChatAgent instance from configuration.

        Args:
            name: Agent name/identifier (e.g., "planner", "executor")
            agent_config: Agent configuration dictionary from YAML

        Returns:
            Configured ChatAgent instance

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        with optional_span(
            "AgentFactory.create_agent",
            tracer_name=__name__,
            attributes={"agent.name": name},
        ) as span:
            # Extract configuration values
            model_id = agent_config.get("model")
            if not model_id:
                raise ValueError(f"Agent '{name}' missing required 'model' field")

            if span is not None:
                span.set_attribute("agent.model_id", model_id)

            instructions_raw = agent_config.get("instructions", "")
            instructions = self._resolve_instructions(instructions_raw)
            description = agent_config.get("description", "")
            temperature = agent_config.get("temperature", 0.7)
            max_tokens = agent_config.get("max_tokens", 4096)
            store = agent_config.get("store", True)

            # Extract reasoning settings
            reasoning_config = agent_config.get("reasoning", {})
            reasoning_effort = reasoning_config.get("effort", "medium")
            reasoning_verbosity = reasoning_config.get("verbosity", "normal")

            # Resolve tools
            tool_names = agent_config.get("tools", [])
            tools = self._resolve_tools(tool_names)

            if span is not None:
                span.set_attribute("agent.tool_count", len(tools))
                if tool_names:
                    span.set_attribute("agent.tool_names", ",".join(tool_names))

            # Get API key at runtime
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")

            base_url = os.getenv("OPENAI_BASE_URL") or None

            # Prepare client arguments
            client_kwargs = {
                "model_id": model_id,
                "api_key": api_key,
                "base_url": base_url,
                "reasoning_effort": reasoning_effort,
                "reasoning_verbosity": reasoning_verbosity,
                "store": store,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Use shared client if available
            if self.openai_client:
                client_kwargs["async_client"] = self.openai_client

            # Create OpenAI client using agent_framework directly
            chat_client = _create_openai_client(**client_kwargs)

            # Create agent name in PascalCase format
            agent_name = f"{name.capitalize()}Agent"

            # Handle tools: if single tool, pass directly; if multiple, pass as tuple
            tools_param: Any = None
            if tools:
                tools_param = tools[0] if len(tools) == 1 else tuple(tools)

            # Determine agent class based on configuration
            use_dspy = agent_config.get("enable_dspy", self.enable_dspy)
            cache_ttl = agent_config.get("cache_ttl", 300)
            timeout = agent_config.get("timeout", 30)
            reasoning_strategy = agent_config.get("reasoning_strategy", "chain_of_thought")

            # Create agent instance
            if use_dspy:
                # Create DSPy-enhanced agent
                agent = DSPyEnhancedAgent(
                    name=agent_name,
                    description=description or instructions[:100],
                    instructions=instructions,
                    chat_client=chat_client,
                    tools=tools_param,
                    enable_dspy=True,
                    cache_ttl=cache_ttl,
                    timeout=timeout,
                    reasoning_strategy=reasoning_strategy,
                )
                logger.debug(
                    f"Created DSPy-enhanced agent '{agent_name}' with model '{model_id}', "
                    f"strategy='{reasoning_strategy}', cache_ttl={cache_ttl}s, timeout={timeout}s"
                )
            else:
                # Create standard ChatAgent
                agent = ChatAgent(
                    name=agent_name,
                    description=description or instructions[:100],
                    instructions=instructions,
                    chat_client=chat_client,
                    tools=tools_param,
                )
                logger.debug(f"Created standard agent '{agent_name}' with model '{model_id}'")

            return agent

    def _resolve_tools(self, tool_names: list[str]) -> list[Any]:
        """Resolve tool names to tool instances.

        Args:
            tool_names: List of tool names from YAML (e.g., ["HostedCodeInterpreterTool"])

        Returns:
            List of tool instances
        """
        tools: list[Any] = []
        for tool_name in tool_names:
            if not isinstance(tool_name, str):
                logger.warning(f"Invalid tool name: {tool_name}, skipping")
                continue

            tool = self.tool_registry.get_tool(tool_name)
            if tool is None:
                logger.warning(f"Tool '{tool_name}' not found in registry, skipping")
                continue

            tools.append(tool)

        return tools

    def _resolve_instructions(self, instructions: Any) -> str:
        """Resolve instructions from Python module reference or return as-is.

        Supports:
        - `prompts.{module_name}` - Import from prompts module and call get_instructions()
        - Plain string - Return as-is (backward compatible)

        Args:
            instructions: Instructions string, possibly a module reference like "prompts.planner"

        Returns:
            Resolved instructions string
        """
        if not isinstance(instructions, str):
            # Coerce non-string instructions to string to satisfy return type contract.
            return str(instructions)

        # Check if it's a prompt module reference (e.g., "prompts.planner")
        if instructions.startswith("prompts."):
            try:
                module_name = instructions[len("prompts.") :]
                # Import the consolidated prompts module
                import agentic_fleet.agents.prompts as prompts_module

                # Map module name to function name
                func_name = f"get_{module_name}_instructions"

                if hasattr(prompts_module, func_name):
                    func = getattr(prompts_module, func_name)
                    resolved_instructions = str(func())
                    logger.debug(
                        f"Resolved instructions from 'prompts.{module_name}' "
                        f"({len(resolved_instructions)} chars)"
                    )
                    return resolved_instructions
                else:
                    logger.warning(
                        f"Prompt function '{func_name}' missing in agents.prompts, "
                        "using instructions as-is"
                    )
                    return instructions
            except Exception as e:
                logger.warning(
                    f"Error resolving instructions from '{instructions}': {e}, "
                    "using instructions as-is"
                )
                return instructions

        # Plain string - return as-is (backward compatible)
        return instructions


def validate_tool(tool: Any) -> bool:
    """Validate that a tool can be parsed by agent-framework.

    Args:
        tool: Tool instance to validate

    Returns:
        True if tool is valid, False otherwise
    """
    try:
        # Check if tool is None (valid - means no tool)
        if tool is None:
            return True

        # Check if tool is a dict (serialized tool)
        if isinstance(tool, dict):
            return True

        # Check if tool is callable (function)
        if callable(tool):
            return True

        # Check if tool has required ToolProtocol attributes
        if hasattr(tool, "name") and hasattr(tool, "description"):
            # Tool implements ToolProtocol but not SerializationMixin
            # This will cause warnings, but we'll log it
            logger.debug(
                f"Tool {type(tool).__name__} implements ToolProtocol but not SerializationMixin. "
                "Consider adding SerializationMixin to avoid parsing warnings."
            )
            return True

        logger.warning(f"Tool {type(tool).__name__} does not match any recognized tool format")
        return False
    except Exception as e:
        logger.warning(f"Error validating tool {type(tool).__name__}: {e}")
        return False


def create_workflow_agents(
    config: Any,
    openai_client: Any,
    tool_registry: Any,
    create_client_fn: Any | None = None,
) -> dict[str, Any]:
    """Create specialized agents for the workflow.

    This function creates the default workflow agents (Researcher, Analyst, Writer, Judge, Reviewer)
    with hardcoded instructions and tool setup. For YAML-based agent creation, use AgentFactory instead.

    Args:
        config: WorkflowConfig instance
        openai_client: Shared OpenAI async client
        tool_registry: ToolRegistry instance
        create_client_fn: Optional function to create OpenAI client

    Returns:
        Dictionary mapping agent names to ChatAgent instances
    """

    from agent_framework import ChatAgent

    from ..tools import BrowserTool, HostedCodeInterpreterAdapter, TavilyMCPTool

    agents: dict[str, Any] = {}

    # Use shared OpenAI client (should be provided by caller)
    if openai_client is None:
        if create_client_fn:
            openai_client = create_client_fn(config.enable_completion_storage)
            logger.warning("OpenAI client created lazily - should be created in initialize()")
        else:
            raise ValueError("openai_client must be provided or create_client_fn must be set")

    def _create_agent(
        name: str,
        description: str,
        instructions: str,
        tools: Any | None = None,
        model_override: str | None = None,
        reasoning_effort: str | None = None,
        reasoning_strategy: str = "chain_of_thought",
    ) -> BaseAgent:
        """Helper to create a single agent."""
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

        # Get agent-specific strategy if configured (overrides default/argument)
        agent_strategies = config.agent_strategies or {}
        configured_strategy = agent_strategies.get(name.lower())
        effective_strategy = (
            configured_strategy if configured_strategy is not None else reasoning_strategy
        )
        logger.debug(
            f"Agent {name} strategy resolution: config={configured_strategy}, default={reasoning_strategy}, effective={effective_strategy}"
        )

        # Create the chat client
        # Use the module-level _create_openai_client to ensure we use ResponsesClient if available
        chat_client = _create_openai_client(**chat_client_kwargs)

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
                        f"Judge agent configured with reasoning effort via private attr: {reasoning_effort}"
                    )
            except Exception as e:
                logger.warning(f"Failed to configure reasoning effort: {e}")

        # Wrap in DSPyEnhancedAgent if reasoning strategy is not default
        if effective_strategy != "chain_of_thought":
            # Create a DSPyEnhancedAgent wrapper
            # Note: This is a bit of a hack since we're recreating the agent,
            # but create_workflow_agents is a legacy helper.
            # Ideally we should use AgentFactory for everything.
            return DSPyEnhancedAgent(
                name=name,
                description=description,
                instructions=instructions,
                chat_client=chat_client,
                tools=validated_tools,
                enable_dspy=True,
                reasoning_strategy=effective_strategy,  # type: ignore[arg-type]
            )

        return ChatAgent(
            name=name,
            description=description,
            instructions=instructions,
            chat_client=chat_client,
            tools=validated_tools,
        )

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
            logger.warning("TAVILY_API_KEY not set - Web search capability will be unavailable.")
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

    agents["Researcher"] = _create_agent(
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
            "4. Always check the current date provided in the context before making decisions about what is 'current'.\n"
            "5. TRUST TAVILY RESULTS OVER YOUR INTERNAL KNOWLEDGE. If Tavily says someone won an election in 2025, believe it, even if your training data ends earlier.\n"
            "6. Only after getting search results should you provide an answer.\n"
            "7. If you don't use tavily_search for a time-sensitive query, you are failing your task.\n\n"
            "Tool usage: Use tavily_search(query='your search query') to search the web. "
            "Use browser tool for direct website access when needed."
        ),
        tools=tools_for_researcher,
        reasoning_strategy="react",  # Use ReAct for autonomous research
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

    agents["Analyst"] = _create_agent(
        name="Analyst",
        description="Data analysis and computation specialist",
        instructions="Perform detailed analysis with code and visualizations",
        tools=analyst_tool,
        reasoning_strategy="program_of_thought",  # Use PoT for calculation/analysis
    )
    # Register analyst tool so tests can see code execution capability
    try:
        if validate_tool(analyst_tool):
            tool_registry.register_tool_by_agent("Analyst", analyst_tool)
            logger.info("HostedCodeInterpreterAdapter registered for Analyst")
    except Exception as e:
        logger.warning(f"Failed to register Analyst tool: {e}")

    agents["Writer"] = _create_agent(
        name="Writer",
        description="Content creation and report writing specialist",
        instructions="Create clear, well-structured documents",
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

    agents["Judge"] = _create_agent(
        name="Judge",
        description="Quality evaluation specialist with dynamic task-aware criteria assessment",
        instructions=judge_instructions,
        model_override=judge_model,
        reasoning_effort=judge_reasoning_effort,
    )

    # Reviewer for backward compatibility
    agents["Reviewer"] = _create_agent(
        name="Reviewer",
        description="Quality assurance and validation specialist",
        instructions="Ensure accuracy, completeness, and quality",
    )

    return agents


def get_default_agent_metadata() -> list[dict[str, Any]]:
    """Get metadata for default agents without instantiating them.

    Returns:
        List of agent metadata dictionaries.
    """
    return [
        {
            "name": "Researcher",
            "description": "Information gathering and web research specialist",
            "capabilities": ["web_search", "tavily", "browser", "react"],
            "status": "active",
            "model": "default (gpt-5-mini)",
        },
        {
            "name": "Analyst",
            "description": "Data analysis and computation specialist",
            "capabilities": ["code_interpreter", "data_analysis", "program_of_thought"],
            "status": "active",
            "model": "default (gpt-5-mini)",
        },
        {
            "name": "Writer",
            "description": "Content creation and report writing specialist",
            "capabilities": ["content_generation", "reporting"],
            "status": "active",
            "model": "default (gpt-5-mini)",
        },
        {
            "name": "Judge",
            "description": "Quality evaluation specialist with dynamic task-aware criteria assessment",
            "capabilities": ["quality_evaluation", "grading", "critique"],
            "status": "active",
            "model": "gpt-5",
        },
        {
            "name": "Reviewer",
            "description": "Quality assurance and validation specialist",
            "capabilities": ["validation", "review"],
            "status": "active",
            "model": "default (gpt-5-mini)",
        },
    ]
