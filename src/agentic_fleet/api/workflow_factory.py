"""WorkflowFactory for creating workflows from YAML configuration.

Configuration resolution order:
1. AF_WORKFLOW_CONFIG environment variable (absolute path)
2. config/workflows.yaml (repo/deploy-level override)
3. Package default agentic_fleet/workflows.yaml, falling back to workflow.yaml
"""

from __future__ import annotations

import importlib.resources
import os
from pathlib import Path
from typing import Any, cast

import yaml

from agentic_fleet.api.models.workflow_config import WorkflowConfig
from agentic_fleet.models.workflow import WorkflowConfig as BackendWorkflowConfig


class WorkflowFactory:
    """Factory for creating workflows from YAML configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize WorkflowFactory.

        Args:
            config_path: Optional explicit config path. If not provided, uses
                resolution order: env var -> config/workflows.yaml -> package default.
        """
        if config_path is not None:
            self.config_path = Path(config_path)
            if not self.config_path.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")
        else:
            self.config_path = self._resolve_config_path()

        self._config = self._load_config()

    def _resolve_config_path(self) -> Path:
        """Resolve config path using priority order.

        Priority:
        1. AF_WORKFLOW_CONFIG environment variable (absolute path)
        2. config/workflows.yaml (repo/deploy-level override)
        3. Package default agentic_fleet/workflow.yaml
        """
        # Priority 1: Environment variable
        env_path = os.getenv("AF_WORKFLOW_CONFIG")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path

        # Priority 2: config/workflows.yaml (repo-level override)
        repo_config = Path(__file__).resolve().parents[3] / "config" / "workflows.yaml"
        if repo_config.exists():
            return repo_config

        # Priority 3: Packaged defaults (prefer plural, then singular)
        for candidate in ("workflows.yaml", "workflow.yaml"):
            try:
                with importlib.resources.path("agentic_fleet", candidate) as pkg_path:
                    if Path(pkg_path).exists():
                        return Path(pkg_path)
            except (ModuleNotFoundError, FileNotFoundError):
                continue

        # Fallback: try relative to this file (developer installs)
        for local in ("workflows.yaml", "workflow.yaml"):
            default_path = Path(__file__).parent.parent / local
            if default_path.exists():
                return default_path

        raise FileNotFoundError(
            "No workflow configuration found. Checked:\n"
            "  1. AF_WORKFLOW_CONFIG environment variable\n"
            "  2. config/workflows.yaml\n"
            "  3. Packaged defaults: agentic_fleet/(workflows.yaml|workflow.yaml)"
        )

    def _load_config(self) -> dict[str, Any]:
        """Load YAML configuration from resolved path."""
        with open(self.config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise TypeError("Workflow configuration must be a mapping at the top level.")

        return cast(dict[str, Any], data)

    def list_available_workflows(self) -> list[dict[str, Any]]:
        """List all available workflows from configuration."""
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
        """Get workflow configuration for a specific workflow ID.

        Args:
            workflow_id: The workflow identifier (e.g., "collaboration", "magentic_fleet")

        Returns:
            WorkflowConfig instance

        Raises:
            ValueError: If workflow_id is not found
        """
        workflows = self._config.get("workflows", {})
        if workflow_id not in workflows:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        workflow_data = workflows[workflow_id]
        return WorkflowConfig(
            id=workflow_id,
            name=workflow_data.get("name", workflow_id),
            description=workflow_data.get("description", ""),
            factory=workflow_data.get("factory", ""),
            agents=workflow_data.get("agents", {}),
            manager=workflow_data.get("manager", {}),
        )

    def create_from_yaml(self, workflow_id: str) -> Any:
        """Create a workflow instance from YAML configuration.

        Args:
            workflow_id: The workflow identifier

        Returns:
            Workflow instance (type depends on factory function)

        Raises:
            ValueError: If workflow_id is not found or factory function doesn't exist
        """
        cfg = self.get_workflow_config(workflow_id)

        # Resolve agent module references and manager prompt modules
        resolved_cfg = self._resolve_workflow_config(cfg)

        backend_cfg = BackendWorkflowConfig(
            id=resolved_cfg.id,
            name=resolved_cfg.name,
            description=resolved_cfg.description,
            factory=resolved_cfg.factory,
            agents={name: dict(agent_cfg) for name, agent_cfg in resolved_cfg.agents.items()},
            manager=dict(resolved_cfg.manager),
        )

        # Map factory names to builders
        factory_name = (resolved_cfg.factory or "").strip()

        if factory_name in {"create_magentic_fleet_workflow", "magentic_fleet"}:
            from agentic_fleet.workflow.magentic_workflow import MagenticFleetWorkflowBuilder

            builder = MagenticFleetWorkflowBuilder()
            return builder.build(backend_cfg)

        raise ValueError(
            f"Unsupported workflow factory '{factory_name}' for workflow '{workflow_id}'"
        )

    def _resolve_workflow_config(self, cfg: WorkflowConfig) -> WorkflowConfig:
        """Resolve module references in agents and manager instructions.

        - agents: if value is a string like 'agents.planner', import
          agentic_fleet.agents.planner.get_config() and use returned dict.
        - manager.instructions: if string like 'prompts.xxx', import
          agentic_fleet.prompts.xxx.get_instructions() and use returned str.
        """
        agents: dict[str, dict[str, Any]] = {}
        for name, agent_value in cfg.agents.items():
            if isinstance(agent_value, str) and agent_value.startswith("agents."):
                module_name = agent_value[len("agents.") :]
                try:
                    import importlib

                    mod = importlib.import_module(f"agentic_fleet.agents.{module_name}")
                    if hasattr(mod, "get_config"):
                        agents[name] = dict(mod.get_config())
                    else:
                        raise AttributeError(f"agents.{module_name} missing get_config()")
                except Exception as exc:  # pragma: no cover - defensive
                    raise ValueError(
                        f"Failed to resolve agent '{name}' from '{agent_value}': {exc}"
                    ) from exc
            elif isinstance(agent_value, dict):
                agents[name] = dict(agent_value)
            else:
                raise TypeError(f"Agent '{name}' config must be dict or 'agents.*' string")

        # Manager: resolve instructions module reference if present
        manager = dict(cfg.manager)
        instructions = manager.get("instructions")
        if isinstance(instructions, str) and instructions.startswith("prompts."):
            try:
                import importlib

                mod = importlib.import_module(f"agentic_fleet.{instructions}")
                if hasattr(mod, "get_instructions"):
                    manager["instructions"] = str(mod.get_instructions())
            except Exception:  # best-effort; leave as-is on failure
                pass

        return WorkflowConfig(
            id=cfg.id,
            name=cfg.name,
            description=cfg.description,
            factory=cfg.factory,
            agents=cast(dict[str, Any], agents),
            manager=manager,
        )

    def _build_collaboration_args(self, config: WorkflowConfig) -> dict[str, Any]:
        """Build arguments for collaboration workflow factory."""
        # Placeholder - full implementation depends on workflow.py structure
        return {}

    def _build_magentic_fleet_args(self, config: WorkflowConfig) -> dict[str, Any]:
        """Build arguments for magentic fleet workflow factory."""
        # Placeholder - full implementation depends on workflow.py structure
        return {}
