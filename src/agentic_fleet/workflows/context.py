from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import openai

from ..dspy_modules.reasoner import DSPyReasoner
from ..utils.cache import TTLCache
from ..utils.history_manager import HistoryManager
from ..utils.progress import NullProgressCallback, ProgressCallback
from ..utils.tool_registry import ToolRegistry
from .config import WorkflowConfig
from .handoff import HandoffManager

# Direct import - no circular dependency detected
from .compilation import CompilationState


@dataclass
class SupervisorContext:
    """Container for SupervisorWorkflow orchestration state."""

    config: WorkflowConfig
    dspy_supervisor: DSPyReasoner | None = None
    agents: dict[str, Any] | None = None
    workflow: Any = None
    verbose_logging: bool = True

    openai_client: openai.AsyncOpenAI | None = None
    tool_registry: ToolRegistry | None = None
    history_manager: HistoryManager | None = None
    handoff: HandoffManager | None = None
    enable_handoffs: bool = True

    analysis_cache: TTLCache[str, dict[str, Any]] | None = None
    latest_phase_timings: dict[str, float] = field(default_factory=dict)
    latest_phase_status: dict[str, str] = field(default_factory=dict)

    progress_callback: ProgressCallback = field(default_factory=NullProgressCallback)
    current_execution: dict[str, Any] = field(default_factory=dict)
    execution_history: list[dict[str, Any]] = field(default_factory=list)

    compilation_status: str = "pending"
    compilation_task: asyncio.Task[Any] | None = None
    compilation_lock: asyncio.Lock | None = None
    compilation_state: CompilationState | None = None
