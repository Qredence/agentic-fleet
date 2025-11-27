"""Agent factory for creating ChatAgent instances from YAML configuration."""

from __future__ import annotations

import importlib
import inspect
import logging
import warnings
from pathlib import Path
from typing import Any

import dspy
import yaml
from agent_framework._agents import ChatAgent
from agent_framework.openai import OpenAIResponsesClient
from dotenv import load_dotenv

from agentic_fleet.agents.base import DSPyEnhancedAgent
from agentic_fleet.dspy_modules.agent_signatures import PlannerInstructionSignature
from agentic_fleet.utils.env import env_config
from agentic_fleet.utils.telemetry import optional_span
from agentic_fleet.utils.tool_registry import ToolRegistry

try:
    from agent_framework.openai import OpenAIResponsesClient as _PreferredOpenAIClient

    _RESPONSES_CLIENT_AVAILABLE = True
except ImportError:
    from agent_framework.openai import OpenAIChatClient as _PreferredOpenAIClient  # type: ignore

    _RESPONSES_CLIENT_AVAILABLE = False

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
        self.enable_dspy = env_config.enable_dspy_agents

        self.instruction_generator = None
        if self.enable_dspy:
            try:
                self.instruction_generator = dspy.ChainOfThought(PlannerInstructionSignature)
            except Exception as e:
                logger.warning(f"Failed to initialize DSPy instruction generator: {e}")

    def create_agent(
        self,
        name: str,
        agent_config: dict[str, Any],
    ) -> ChatAgent:
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
            workflow_ref = agent_config.get("workflow")
            if workflow_ref:
                return self._create_workflow_agent(name, workflow_ref, agent_config)

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

            # Resolve context providers
            context_provider_names = agent_config.get("context_providers", [])
            context_providers = self._resolve_context_providers(context_provider_names)

            if span is not None:
                span.set_attribute("agent.tool_count", len(tools))
                if tool_names:
                    span.set_attribute("agent.tool_names", ",".join(tool_names))
                if context_provider_names:
                    span.set_attribute("agent.context_providers", ",".join(context_provider_names))

            # Get API key at runtime
            api_key = env_config.openai_api_key
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")

            base_url = env_config.openai_base_url

            # Create OpenAI client using agent_framework directly
            # Use shared async_client if available for proper resource reuse
            chat_client = OpenAIResponsesClient(
                model_id=model_id,
                api_key=api_key,
                base_url=base_url,
                async_client=self.openai_client,  # Reuse shared client instance
                reasoning_effort=reasoning_effort,
                reasoning_verbosity=reasoning_verbosity,
                store=store,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Create agent name in PascalCase format
            agent_name = f"{name.capitalize()}Agent"

            # Handle tools: pass as list
            tools_param: Any = tools if tools else None

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
                    context_providers=context_providers,
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
                    context_providers=context_providers,
                )
                logger.debug(f"Created standard agent '{agent_name}' with model '{model_id}'")

            return agent

    def _create_workflow_agent(
        self,
        name: str,
        workflow_ref: str,
        agent_config: dict[str, Any],
    ) -> ChatAgent:
        """Create an agent from a workflow definition.

        Args:
            name: Agent name
            workflow_ref: Reference to workflow class (module.Class)
            agent_config: Agent configuration

        Returns:
            ChatAgent instance wrapping the workflow
        """
        try:
            # Parse module and class
            if "." not in workflow_ref:
                raise ValueError(f"Invalid workflow reference: {workflow_ref}")

            module_name, class_name = workflow_ref.rsplit(".", 1)
            module = importlib.import_module(module_name)
            workflow_cls = getattr(module, class_name)

            # Instantiate workflow with configuration if available
            # Pass configuration if available; fallback to no-arg constructor for legacy support.
            init_kwargs = agent_config.get("init_kwargs") or agent_config.get("config") or {}
            workflow = workflow_cls(**init_kwargs) if init_kwargs else workflow_cls()

            # Wrap as agent
            if hasattr(workflow, "as_agent"):
                agent = workflow.as_agent()
                # Override name/description if provided
                # Note: as_agent() might return a specific Agent subclass
                # We try to set attributes if possible
                if name and hasattr(agent, "name"):
                    agent.name = name
                if agent_config.get("description") and hasattr(agent, "description"):
                    agent.description = agent_config.get("description")
                return agent
            else:
                raise ValueError(f"Workflow class {class_name} does not have as_agent() method")

        except Exception as e:
            logger.error(f"Failed to create workflow agent {name}: {e}")
            raise

    def _resolve_context_providers(self, provider_names: list[str]) -> list[Any]:
        """Resolve context provider names to instances.

        Args:
            provider_names: List of provider names from YAML

        Returns:
            List of context provider instances
        """
        providers: list[Any] = []
        import agentic_fleet.tools as fleet_tools

        for name in provider_names:
            if not isinstance(name, str):
                continue

            if hasattr(fleet_tools, name):
                try:
                    cls = getattr(fleet_tools, name)
                    instance = cls()
                    providers.append(instance)
                    logger.debug(f"Instantiated context provider '{name}' from fleet_tools")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to instantiate context provider '{name}': {e}")
                    continue

            logger.warning(f"Context provider '{name}' not found, skipping")

        return providers

    def _resolve_tools(self, tool_names: list[str]) -> list[Any]:
        """Resolve tool names to tool instances.

        Args:
            tool_names: List of tool names from YAML (e.g., ["HostedCodeInterpreterTool"])

        Returns:
            List of tool instances
        """
        tools: list[Any] = []
        # Import tools module dynamically to avoid circular imports
        import agentic_fleet.tools as fleet_tools

        for tool_name in tool_names:
            if not isinstance(tool_name, str):
                logger.warning(f"Invalid tool name: {tool_name}, skipping")
                continue

            # First check registry
            tool_meta = self.tool_registry.get_tool(tool_name)
            if tool_meta and tool_meta.tool_instance:
                tools.append(tool_meta.tool_instance)
                continue

            # Then check if it's a class in fleet_tools
            if hasattr(fleet_tools, tool_name):
                try:
                    tool_cls = getattr(fleet_tools, tool_name)
                    # Instantiate with no args (relying on env vars)
                    tool_instance = tool_cls()
                    tools.append(tool_instance)
                    logger.debug(f"Instantiated tool '{tool_name}' from fleet_tools")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to instantiate tool '{tool_name}': {e}")
                    continue

            logger.warning(f"Tool '{tool_name}' not found in registry or fleet_tools, skipping")

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

                # Dynamic generation for planner
                if module_name == "planner" and self.instruction_generator:
                    try:
                        # Get default agents for context
                        default_agents = get_default_agent_metadata()
                        agents_desc = "\n".join(
                            [f"- {a['name']}: {a['description']}" for a in default_agents]
                        )

                        result = self.instruction_generator(
                            available_agents=agents_desc,
                            workflow_goal="Coordinate the multi-agent system to solve complex user tasks efficiently by planning, delegating, and verifying work.",
                        )
                        logger.info("Generated dynamic planner instructions using DSPy")
                        return result.agent_instructions
                    except Exception as e:
                        logger.warning(f"Failed to generate dynamic planner instructions: {e}")
                        # Fallback to static below

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


def _resolve_workflow_config_path(config_path: str | Path | None = None) -> Path:
    """Resolve the workflow configuration path.

    Args:
        config_path: Optional override for the workflow config location.

    Returns:
        Path to the workflow configuration file.
    """

    if config_path:
        candidate = Path(config_path).expanduser().resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"Workflow config not found at: {candidate}")
        return candidate

    # src/agentic_fleet/config/workflow_config.yaml
    primary = Path(__file__).resolve().parent.parent / "config" / "workflow_config.yaml"
    if primary.exists():
        return primary

    # Repository root fallback (../../../../config/workflow_config.yaml)
    fallback = (
        Path(__file__).resolve().parent.parent.parent.parent / "config" / "workflow_config.yaml"
    )
    if fallback.exists():
        return fallback

    raise FileNotFoundError("Unable to locate workflow_config.yaml")


def create_workflow_agents(
    config_path: str | Path | None = None,
    *,
    tool_registry: ToolRegistry | None = None,
    openai_client: Any | None = None,
    agent_models: dict[str, str] | None = None,
) -> dict[str, ChatAgent]:
    """Create workflow agents from the declarative YAML configuration.

    This helper preserves the legacy interface used by older modules that
    expected a `create_workflow_agents()` factory. Internally it defers to the
    modern :class:`AgentFactory` so that all validation and tool resolution
    logic stays in one place.
    """

    warnings.warn(
        "create_workflow_agents is deprecated; use AgentFactory directly",
        DeprecationWarning,
        stacklevel=2,
    )

    resolved_path = _resolve_workflow_config_path(config_path)
    with resolved_path.open("r", encoding="utf-8") as stream:
        config_data = yaml.safe_load(stream) or {}

    yaml_agent_configs = config_data.get("agents", {}) or {}
    factory = AgentFactory(tool_registry=tool_registry, openai_client=openai_client)

    created_agents: dict[str, ChatAgent] = {}
    for name, cfg in yaml_agent_configs.items():
        if not isinstance(cfg, dict):
            logger.warning("Skipping agent '%s' with invalid configuration", name)
            continue

        config_copy = dict(cfg)
        model_overrides = agent_models or {}
        override = model_overrides.get(name.lower())
        if override:
            config_copy["model"] = override

        try:
            created_agents[name] = factory.create_agent(name, config_copy)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to create agent '%s': %s", name, exc, exc_info=True)
            raise

    logger.info("Created %d workflow agents from %s", len(created_agents), resolved_path)
    return created_agents
