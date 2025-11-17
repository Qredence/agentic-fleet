"""Workflow initialization utilities.

Extracted from SupervisorWorkflow to support fleet workflow initialization.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from ..agents import create_workflow_agents, validate_tool
from ..dspy_modules.supervisor import DSPySupervisor
from ..utils.agent_framework_shims import ensure_agent_framework_shims
from ..utils.cache import TTLCache
from ..utils.dspy_manager import configure_dspy_settings
from ..utils.history_manager import HistoryManager
from ..utils.logger import setup_logger
from ..utils.tool_registry import ToolRegistry
from .compilation import CompilationState, compile_supervisor_async, get_compiled_supervisor
from .config import WorkflowConfig
from .handoff_manager import HandoffManager
from .orchestration import SupervisorContext
from .utils import create_openai_client_with_store

logger = setup_logger(__name__)


async def initialize_workflow_context(
    config: WorkflowConfig | None = None,
    compile_dspy: bool = True,
    dspy_supervisor: DSPySupervisor | None = None,
) -> SupervisorContext:
    """Initialize workflow context with agents, DSPy supervisor, and tools.

    Args:
        config: Workflow configuration (defaults to WorkflowConfig())
        compile_dspy: Whether to compile DSPy supervisor
        dspy_supervisor: Optional pre-initialized DSPy supervisor to reuse

    Returns:
        Initialized SupervisorContext
    """
    config = config or WorkflowConfig()
    ensure_agent_framework_shims()

    init_start = datetime.now()
    logger.info("=" * 80)
    logger.info("Initializing DSPy-Enhanced Agent Framework")
    logger.info("=" * 80)

    # Validate required environment variables
    try:
        from ..utils.env import validate_agentic_fleet_env

        validate_agentic_fleet_env()
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        raise

    # Create shared OpenAI client once (reused for all agents and supervisor)
    openai_client = create_openai_client_with_store(config.enable_completion_storage)
    logger.info("Created shared OpenAI client for all agents")

    # Initialize DSPy using centralized manager
    logger.info(f"Configuring DSPy with OpenAI LM ({config.dspy_model})")
    configure_dspy_settings(
        model=config.dspy_model,
        enable_cache=True,
        force_reconfigure=False,
    )

    # Create tool registry first
    tool_registry = ToolRegistry()

    # Create DSPy supervisor with enhanced signatures enabled (reuse if provided)
    dspy_supervisor = dspy_supervisor or DSPySupervisor(use_enhanced_signatures=True)

    # Create specialized agents BEFORE compilation if tool-aware DSPy signatures need visibility
    logger.info("Creating specialized agents...")
    agents = create_workflow_agents(
        config=config,
        openai_client=openai_client,
        tool_registry=tool_registry,
        create_client_fn=lambda enable_storage: create_openai_client_with_store(enable_storage),
    )
    logger.info(f"Created {len(agents)} agents: {', '.join(agents.keys())}")

    # Register tools in registry early so supervisor sees them during compilation / analysis
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

    # Attach tool registry to supervisor
    dspy_supervisor.set_tool_registry(tool_registry)

    # Initialize handoff manager (will be updated after compilation)
    compilation_state = CompilationState()

    def get_compiled_supervisor_fn():
        return get_compiled_supervisor(dspy_supervisor, compilation_state)

    handoff_manager = HandoffManager(
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
        handoff_manager=handoff_manager,
        enable_handoffs=config.enable_handoffs,
        analysis_cache=analysis_cache,
        latest_phase_timings={},
        latest_phase_status={},
        progress_callback=None,
        current_execution={},
        execution_history=[],
        compilation_status="pending",
        compilation_task=None,
        compilation_lock=asyncio.Lock(),
        compilation_state=compilation_state,
    )

    # Optionally compile DSPy supervisor
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

    init_time = (datetime.now() - init_start).total_seconds()
    logger.info(f"Workflow context initialized successfully in {init_time:.2f}s")
    logger.info("=" * 80)

    return context
