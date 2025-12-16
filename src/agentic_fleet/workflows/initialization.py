"""Workflow initialization utilities.

Extracted from SupervisorWorkflow to support fleet workflow initialization.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ..agents import AgentFactory, validate_tool
from ..dspy_modules.lifecycle import configure_dspy_settings
from ..dspy_modules.reasoner import DSPyReasoner
from ..utils.agent_framework_shims import ensure_agent_framework_shims
from ..utils.cache import TTLCache
from ..utils.cfg import load_config, validate_agentic_fleet_env
from ..utils.history_manager import HistoryManager
from ..utils.logger import setup_logger
from ..utils.tool_registry import ToolRegistry
from ..utils.tracing import initialize_tracing
from .config import WorkflowConfig
from .context import (
    CompilationState,
    SupervisorContext,
    compile_supervisor_async,
    get_compiled_supervisor,
)
from .handoff import HandoffManager
from .helpers import create_openai_client_with_store

if TYPE_CHECKING:
    from openai import AsyncOpenAI

logger = setup_logger(__name__)


def _validate_environment() -> None:
    """Validate required environment variables."""
    try:
        validate_agentic_fleet_env()
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        raise


def _create_shared_components(
    config: WorkflowConfig,
) -> tuple[AsyncOpenAI, ToolRegistry]:
    """Create and configure shared components (OpenAI client, DSPy, ToolRegistry)."""
    # Create shared OpenAI client once (reused for all agents and supervisor)
    openai_client = create_openai_client_with_store(config.enable_completion_storage)
    logger.info("Created shared OpenAI client for all agents")

    # Initialize DSPy using centralized manager
    logger.info(f"Configuring DSPy with OpenAI LM ({config.dspy_model})")
    configure_dspy_settings(
        model=config.dspy_model,
        enable_cache=True,
        force_reconfigure=False,
        temperature=config.dspy_temperature,
        max_tokens=config.dspy_max_tokens,
    )

    # Create tool registry
    tool_registry = ToolRegistry()

    return openai_client, tool_registry


def _register_agent_tools(agents: dict[str, Any], tool_registry: ToolRegistry) -> None:
    """Register tools from agents into the registry."""
    logger.info("Registering tools in tool registry (pre-compilation)...")
    for agent_name, agent in agents.items():
        registered_count = 0
        failed_count = 0
        try:
            raw_tools = []
            if hasattr(agent, "chat_options") and getattr(agent.chat_options, "tools", None):
                raw_tools = agent.chat_options.tools or []
            elif hasattr(agent, "tools") and getattr(agent, "tools", None):
                raw = agent.tools
                raw_tools = raw if isinstance(raw, list) else [raw]

            for t in raw_tools:
                if t is None:
                    continue
                try:
                    # Validate tool before registration
                    if not validate_tool(t):
                        tool_name = getattr(t, "name", t.__class__.__name__)
                        logger.warning(
                            f"Skipping invalid tool '{tool_name}' for {agent_name}. "
                            "Tool does not match agent-framework requirements."
                        )
                        failed_count += 1
                        continue

                    tool_registry.register_tool_by_agent(agent_name, t)
                    registered_count += 1
                    tool_name = getattr(t, "name", t.__class__.__name__)
                    logger.info(
                        f"Registered tool for {agent_name}: {tool_name} (type: {type(t).__name__})"
                    )
                except Exception as tool_error:
                    tool_name = getattr(t, "name", t.__class__.__name__)
                    logger.warning(
                        f"Failed to register tool '{tool_name}' for {agent_name}: {tool_error}",
                        exc_info=True,
                    )
                    failed_count += 1

        except Exception as e:
            logger.warning(f"Failed to register tools for {agent_name}: {e}", exc_info=True)

        if registered_count > 0:
            logger.debug(f"{agent_name}: {registered_count} tool(s) registered successfully")
        if failed_count > 0:
            logger.warning(f"{agent_name}: {failed_count} tool(s) failed to register")

    total_tools = len(tool_registry.get_available_tools())
    logger.info(
        f"Tool registry initialized with {total_tools} tool(s) across {len(agents)} agent(s)"
    )


def _setup_dspy_compilation(
    context: SupervisorContext,
    config: WorkflowConfig,
    dspy_supervisor: DSPyReasoner,
    agents: dict[str, Any],
    compile_dspy: bool,
) -> None:
    """Setup and optionally start DSPy compilation."""
    compilation_state = context.compilation_state
    if compilation_state is None:
        return

    if compile_dspy and config.compile_dspy:
        logger.info("Setting up DSPy compilation (lazy/background mode)...")
        # Start background compilation task (non-blocking)
        compilation_task = asyncio.create_task(
            compile_supervisor_async(
                supervisor=dspy_supervisor,
                config=config,
                agents=agents,
                progress_callback=None,  # Can be set via context later
                state=compilation_state,
            )
        )
        compilation_state.compilation_task = compilation_task
        context.compilation_task = compilation_task
        context.compilation_status = "compiling"

        logger.info("DSPy compilation started in background (workflow can start immediately)")
    else:
        logger.info("Skipping DSPy compilation (using base prompts)")
        compilation_state.compilation_status = "skipped"
        context.compilation_status = "skipped"


async def initialize_workflow_context(
    config: WorkflowConfig | None = None,
    compile_dspy: bool = True,
    dspy_supervisor: DSPyReasoner | None = None,
) -> SupervisorContext:
    """
    Initialize and return a SupervisorContext populated with agents, tools, a DSPy reasoner, and shared runtime components.

    This prepares the runtime by validating the environment, creating a shared OpenAI client and tool registry, loading or constructing a DSPyReasoner (with an optional compiled-artifact fallback), loading agent definitions from workflow_config.yaml, registering agent tools, attaching the tool registry to the reasoner, and assembling handoff, history, and analysis cache components into a SupervisorContext. Compilation is marked as skipped for offline/runtime compilation according to configuration.

    Parameters:
        config: Workflow configuration object (defaults to a new WorkflowConfig instance when omitted).
        compile_dspy: Whether to attempt runtime DSPy compilation (Offline Layer setups mark compilation as skipped).
        dspy_supervisor: Optional pre-initialized DSPyReasoner to reuse instead of loading or creating one.

    Returns:
        SupervisorContext populated with configuration, agents, the DSPyReasoner, tool registry, handoff manager, history manager, optional analysis cache, and compilation metadata.

    Raises:
        RuntimeError: If a compiled DSPy artifact is required by configuration but not found.
        FileNotFoundError: If the workflow configuration file cannot be found.
        Exception: If agent creation fails for any configured agent.
    """
    config = config or WorkflowConfig()
    ensure_agent_framework_shims()

    init_start = datetime.now()
    logger.info("=" * 80)
    logger.info("Initializing DSPy-Enhanced Agent Framework")
    logger.info("=" * 80)

    _validate_environment()

    # Initialize tracing if enabled.
    #
    # IMPORTANT: `WorkflowConfig` is a lightweight runtime dataclass and does not
    # include the full `tracing:` section from `config/workflow_config.yaml`.
    # Use the YAML config loader here so that `tracing.enabled: true` actually
    # activates tracing without requiring env flags.
    tracing_config: dict[str, Any]
    try:
        tracing_config = load_config(validate=False)
    except Exception:
        # Fall back to dataclass values (env vars may still enable tracing).
        tracing_config = config.config

    initialize_tracing(tracing_config)

    openai_client, tool_registry = _create_shared_components(config)

    # Create DSPy reasoner with enhanced signatures enabled (reuse if provided)
    if dspy_supervisor is None:
        # Try to load compiled artifact first (Offline Layer directive)
        from ..utils.compiler import load_compiled_module

        compiled_path = ".var/logs/compiled_supervisor.pkl"
        loaded_supervisor = load_compiled_module(compiled_path)

        if loaded_supervisor and isinstance(loaded_supervisor, DSPyReasoner):
            logger.info(f"Loaded compiled DSPy supervisor from {compiled_path}")
            dspy_supervisor = loaded_supervisor
        else:
            if config.require_compiled:
                raise RuntimeError(
                    f"Compiled DSPy artifact not found at {compiled_path} and "
                    "dspy.require_compiled is enabled. Run 'agentic-fleet optimize' "
                    "to compile DSPy modules, or set dspy.require_compiled=false "
                    "in workflow_config.yaml to allow zero-shot fallback."
                )
            logger.warning(
                "No compiled supervisor found, using zero-shot reasoner. "
                "Performance may be degraded. Run 'agentic-fleet optimize' for offline compilation."
            )
            # Read typed signature settings from config (DSPy 3.x Pydantic support)
            use_typed = getattr(config, "use_typed_signatures", True)
            enable_cache = getattr(config, "enable_routing_cache", True)
            cache_ttl = getattr(config, "routing_cache_ttl_seconds", 300)
            dspy_supervisor = DSPyReasoner(
                use_enhanced_signatures=True,
                use_typed_signatures=use_typed,
                enable_routing_cache=enable_cache,
                cache_ttl_seconds=cache_ttl,
            )
    elif not getattr(dspy_supervisor, "use_enhanced_signatures", False):
        logger.warning(
            "Provided dspy_supervisor does not have use_enhanced_signatures=True. "
            "This may lead to inconsistent behavior."
        )

    # Create AgentFactory
    agent_factory = AgentFactory(tool_registry=tool_registry, openai_client=openai_client)

    # Load agent configurations from YAML
    from pathlib import Path

    import yaml

    # Try to load from src/agentic_fleet/config/workflow_config.yaml
    config_path = Path(__file__).parent.parent / "config" / "workflow_config.yaml"

    # Fallback to root config if not found (for development environment)
    if not config_path.exists():
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "workflow_config.yaml"

    try:
        with open(config_path) as f:
            full_config = yaml.safe_load(f)
            agent_configs = full_config.get("agents", {})
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise

    agents = {}
    for name, agent_config in agent_configs.items():
        try:
            # Allow workflow config to override model
            agent_models = config.agent_models or {}
            model_override = agent_models.get(name.lower())
            if model_override:
                agent_config["model"] = model_override

            agents[name] = agent_factory.create_agent(name, agent_config)
            logger.info(f"Successfully created agent: {name}")
        except Exception as e:
            logger.error(f"Failed to create agent '{name}': {e}", exc_info=True)
            raise  # Or continue with other agents depending on requirements

    logger.info(f"Created {len(agents)} agents: {', '.join(agents.keys())}")

    _register_agent_tools(agents, tool_registry)

    # Attach tool registry to reasoner
    dspy_supervisor.set_tool_registry(tool_registry)

    # Initialize handoff manager (will be updated after compilation)
    compilation_state = CompilationState()

    def get_compiled_supervisor_fn():
        return get_compiled_supervisor(dspy_supervisor, compilation_state)

    handoff = HandoffManager(
        dspy_supervisor,
        get_compiled_supervisor=get_compiled_supervisor_fn,
    )

    # Create analysis cache
    analysis_cache = (
        TTLCache[str, dict[str, Any]](config.analysis_cache_ttl_seconds)
        if config.analysis_cache_ttl_seconds > 0
        else None
    )

    # Create supervisor context
    context = SupervisorContext(
        config=config,
        dspy_supervisor=dspy_supervisor,
        agents=agents,
        workflow=None,
        verbose_logging=True,
        openai_client=openai_client,
        tool_registry=tool_registry,
        history_manager=HistoryManager(history_format=config.history_format),
        handoff=handoff,
        enable_handoffs=config.enable_handoffs,
        analysis_cache=analysis_cache,
        latest_phase_timings={},
        latest_phase_status={},
        current_execution={},
        execution_history=[],
        compilation_status="pending",
        compilation_task=None,
        compilation_lock=asyncio.Lock(),
    )

    # Register middlewares
    from ..core.middleware import BridgeMiddleware

    if context.history_manager:
        context.middlewares.append(BridgeMiddleware(context.history_manager))

    # Optionally compile DSPy supervisor
    if compile_dspy and config.compile_dspy:
        # Runtime compilation is disabled (Offline Layer architecture).
        # Use `agentic-fleet optimize` for offline compilation.
        logger.info("Runtime DSPy compilation is disabled (Offline Layer architecture).")
        logger.info("Using loaded artifact or zero-shot prompts.")
        compilation_state.compilation_status = "skipped"
        context.compilation_status = "skipped"
    else:
        logger.info("Skipping DSPy compilation (using base prompts)")
        compilation_state.compilation_status = "skipped"
        context.compilation_status = "skipped"

    init_time = (datetime.now() - init_start).total_seconds()
    logger.info(f"Workflow context initialized successfully in {init_time:.2f}s")
    logger.info("=" * 80)

    return context
