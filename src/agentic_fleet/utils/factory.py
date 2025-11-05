"""WorkflowFactory for creating workflows from YAML configuration.

Configuration resolution order (consolidated):
1. ``AF_WORKFLOW_CONFIG`` environment variable (absolute path override)
2. Packaged default ``agentic_fleet/workflows.yaml``

The previous repo-level override (``config/workflows.yaml``) has been removed to
reduce divergence between environments. Runtime workflow selection is achieved
via the *workflow_id* parameter passed to factory methods / API surfaces - no
environment variable controls which workflow is active. If an unknown
``workflow_id`` is requested during *creation*, the factory logs a warning and
falls back to the default workflow instead of raising (config lookup still
raises for invalid IDs to preserve validation semantics).
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.resources
import logging
import os
import warnings
from collections.abc import Callable, Coroutine, Iterator
from pathlib import Path
from typing import Any, TypeVar, cast

import yaml

from agentic_fleet.models.events import RunsWorkflow
from agentic_fleet.models.workflow import WorkflowConfig
from agentic_fleet.utils.logging import sanitize_for_log

T = TypeVar("T")

logger = logging.getLogger(__name__)

# Module-level cache for imported agent modules
_AGENT_MODULE_CACHE: dict[str, Any] = {}


DEFAULT_WORKFLOW_ID = "magentic_fleet"


class WorkflowFactory:
    """Factory for creating workflows from YAML configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize WorkflowFactory.

        Args:
            config_path: Optional explicit config path. If not provided, uses
                resolution order: env var -> packaged default.
        """

        self.config_path = self._determine_config_path(config_path)

        with open(self.config_path, encoding="utf-8") as f:
            content = f.read()
            self._config: dict[str, Any] = yaml.safe_load(content) or {}

    def _determine_config_path(self, override: Path | None) -> Path:
        """Determine which configuration path to use."""

        if override is not None:
            path = Path(override)
            if not path.exists():
                raise FileNotFoundError(f"Configuration file not found: {override}")
            return path

        return self._resolve_config_path()

    @staticmethod
    def _resolve_config_path() -> Path:
        """Resolve config path using priority order.

        Priority:
        1. AF_WORKFLOW_CONFIG environment variable (absolute path)
        2. Packaged default ``agentic_fleet/workflows.yaml``
        """
        # Priority 1: Environment variable
        env_path = os.getenv("AF_WORKFLOW_CONFIG")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path

        # Package default
        try:
            with importlib.resources.path("agentic_fleet", "workflows.yaml") as pkg_path:
                return Path(pkg_path)
        except (ModuleNotFoundError, FileNotFoundError) as exc:
            # Fallback: try relative to this file (development workspace)
            default_path = Path(__file__).parent.parent.parent / "workflow.yaml"
            if default_path.exists():
                return default_path
            raise FileNotFoundError(
                "No workflow configuration found. Checked:\n"
                "  1. AF_WORKFLOW_CONFIG environment variable\n"
                "  2. Packaged default agentic_fleet/workflow.yaml"
            ) from exc

    def list_available_workflows(self) -> list[dict[str, Any]]:
        """List workflows synchronously.

        Returns:
            List of workflow metadata dictionaries.

        Raises:
            RuntimeError: If called from within a running event loop.
        """

        return self._run_blocking(self.list_available_workflows_async)

    async def list_available_workflows_async(self) -> list[dict[str, Any]]:
        """List all available workflows from configuration."""
        assert self._config is not None

        workflows = []
        for workflow_id, workflow_config in self._config.get("workflows", {}).items():
            agent_count = len(workflow_config.get("agents", {}))
            workflows.append(
                {
                    "id": workflow_id,
                    "name": workflow_config.get("name", workflow_id),
                    "description": workflow_config.get("description", ""),
                    "factory": workflow_config.get("factory", ""),
                    "agent_count": agent_count,
                }
            )
        return workflows

    def get_workflow_config(self, workflow_id: str) -> WorkflowConfig:
        """Synchronous wrapper around :meth:`get_workflow_config_async`."""

        return self._run_blocking(lambda: self.get_workflow_config_async(workflow_id))

    async def get_workflow_config_async(self, workflow_id: str) -> WorkflowConfig:
        """Get workflow configuration for a specific workflow ID.

        Args:
            workflow_id: The workflow identifier (e.g., "collaboration", "magentic_fleet")

        Returns:
            WorkflowConfig instance

        Raises:
            ValueError: If workflow_id is not found
        """
        assert self._config is not None

        workflows = self._config.get("workflows", {})
        if workflow_id not in workflows:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        workflow_data = workflows[workflow_id]

        # Resolve agent configs in parallel (may be Python module references or inline dicts)
        agents_raw = workflow_data.get("agents", {})
        agent_names = list(agents_raw.keys())
        agent_configs = list(agents_raw.values())

        # Parallelize agent config resolution
        resolved_configs = [self._resolve_agent_config(config) for config in agent_configs]

        agents_resolved: dict[str, dict[str, Any]] = dict(
            zip(agent_names, resolved_configs, strict=True)
        )

        return WorkflowConfig(
            id=workflow_id,
            name=workflow_data.get("name", workflow_id),
            description=workflow_data.get("description", ""),
            factory=workflow_data.get("factory", ""),
            agents=agents_resolved,
            manager=workflow_data.get("manager", {}),
        )

    def create_from_yaml(self, workflow_id: str) -> RunsWorkflow:
        """Synchronous wrapper around :meth:`create_from_yaml_async`."""

        return self._run_blocking(lambda: self.create_from_yaml_async(workflow_id))

    async def create_from_yaml_async(self, workflow_id: str) -> RunsWorkflow:
        """Create a workflow instance from YAML configuration.

        Attempt to build the requested workflow. If the *creation* phase fails
        because the workflow ID is unknown, a warning is emitted and the
        default workflow is used instead. (Direct config access via
        :meth:`get_workflow_config_async` still raises for unknown IDs.)

        Args:
            workflow_id: Requested workflow identifier.

        Returns:
            A workflow instance implementing the *RunsWorkflow* protocol.
        """
        try:
            config = await self.get_workflow_config_async(workflow_id)
        except ValueError:
            if workflow_id != DEFAULT_WORKFLOW_ID:
                logger.warning(
                    "Unknown workflow_id '%s'; falling back to default '%s'",
                    sanitize_for_log(workflow_id),
                    DEFAULT_WORKFLOW_ID,
                )
                config = await self.get_workflow_config_async(DEFAULT_WORKFLOW_ID)
            else:  # pragma: no cover - defensive, should not happen
                raise

        factory_label = config.factory or "create_magentic_fleet_workflow"

        # Currently we only support the magentic fleet builder. Future builders
        # can be added to this dispatch map keyed by factory label.
        if factory_label == "create_magentic_fleet_workflow":
            from agentic_fleet.workflow.magentic_workflow import (
                MagenticFleetWorkflowBuilder,
            )  # local import to avoid cycle

            builder = MagenticFleetWorkflowBuilder()
            return builder.build(config)

        warnings.warn(
            f"Unsupported workflow factory '{factory_label}' - falling back to default builder.",
            DeprecationWarning,
            stacklevel=2,
        )
        from agentic_fleet.workflow.magentic_workflow import MagenticFleetWorkflowBuilder

        return MagenticFleetWorkflowBuilder().build(config)

    class _AwaitableDict(dict[str, Any]):
        """Dict subclass that is also awaitable.

        Some legacy tests *await* the private ``_resolve_agent_config`` method while
        newer code calls it synchronously. To remain backward compatible without
        rewriting all tests (and without converting the method itself to ``async``
        which would break existing synchronous call sites), we return an instance
        of this awaitable dict.  When awaited it simply yields itself.
        """

        def __await__(self) -> Iterator[Any]:  # pragma: no cover - trivial
            async def _coro() -> WorkflowFactory._AwaitableDict:
                # Yield control once to satisfy linters about async context
                await asyncio.sleep(0)
                return self

            return _coro().__await__()

    def _resolve_agent_config(self, agent_config: str | dict[str, Any]) -> dict[str, Any]:
        """Resolve agent configuration from Python module reference or return as-is.

        Supports:
        - `agents.{module_name}` - Import from agents module and call get_config()
        - Inline dict - Return as-is (backward compatible)

        Uses module-level cache for imported agent modules.

        Args:
            agent_config: Agent configuration, either a string like "agents.planner"
                or a dict with inline configuration

        Returns:
            Resolved agent configuration dictionary
        """
        # If it's already a dict, return as-is (backward compatible)
        if isinstance(agent_config, dict):
            return WorkflowFactory._AwaitableDict(agent_config)

        # If it's a string and an agent module reference, resolve it
        if isinstance(agent_config, str) and agent_config.startswith("agents."):
            module_name = agent_config[len("agents.") :]
            full_module_name = f"agentic_fleet.agents.{module_name}"

            # Check cache first
            if full_module_name in _AGENT_MODULE_CACHE:
                agent_module = _AGENT_MODULE_CACHE[full_module_name]
                if hasattr(agent_module, "get_config"):
                    config: dict[str, Any] = agent_module.get_config()
                    return WorkflowFactory._AwaitableDict(config)

            try:
                # Import the agent module dynamically
                agent_module = importlib.import_module(full_module_name)
                _AGENT_MODULE_CACHE[full_module_name] = agent_module

                if hasattr(agent_module, "get_config"):
                    resolved_config: dict[str, Any] = agent_module.get_config()
                    logger.debug(f"Resolved agent config from module 'agents.{module_name}'")
                    return WorkflowFactory._AwaitableDict(resolved_config)
                else:
                    logger.warning(
                        f"Agent module 'agents.{module_name}' missing get_config() function, "
                        "treating as inline config"
                    )
                    return WorkflowFactory._AwaitableDict({"instructions": agent_config})
            except ImportError as e:
                logger.warning(
                    f"Failed to import agent module 'agents.{module_name}': {e}, "
                    "treating as inline config"
                )
                return WorkflowFactory._AwaitableDict({"instructions": agent_config})
            except Exception as e:
                logger.warning(
                    f"Error resolving agent config from '{agent_config}': {e}, "
                    "treating as inline config"
                )
                return WorkflowFactory._AwaitableDict({"instructions": agent_config})

        # Fallback: treat as string value (unlikely but backward compatible)
        return WorkflowFactory._AwaitableDict({"instructions": str(agent_config)})

    # Backward compatibility: tests/mocks expect private method _load_config()
    def _load_config(self) -> dict[str, Any]:  # pragma: no cover - compatibility shim
        """Return raw configuration dictionary (legacy private API).

        Older tests patch or inspect this helper. Kept as a thin shim to avoid
        modifying historical test expectations.
        """
        config = getattr(self, "_config", {})
        return cast(dict[str, Any], config)

    def _run_blocking(self, coroutine_factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
        """Execute coroutine in blocking context, avoiding nested event loops."""

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(coroutine_factory())

        raise RuntimeError(
            "WorkflowFactory synchronous method called inside running event loop. "
            "Use the '*_async' variant instead."
        )
