"""WorkflowFactory for creating workflows from YAML configuration.

Configuration resolution order:
1. AF_WORKFLOW_CONFIG environment variable (absolute path)
2. config/workflows.yaml (repo/deploy-level override)
3. Package default agentic_fleet/workflow.yaml (via importlib.resources)
"""

from __future__ import annotations

import importlib.resources
import os
from pathlib import Path
from typing import Any

import yaml

from agentic_fleet.api.models.workflow_config import WorkflowConfig


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
        repo_config = Path(__file__).parent.parent.parent.parent / "config" / "workflows.yaml"
        if repo_config.exists():
            return repo_config

        # Priority 3: Package default
        try:
            with importlib.resources.path("agentic_fleet", "workflow.yaml") as pkg_path:
                return Path(pkg_path)
        except (ModuleNotFoundError, FileNotFoundError) as exc:
            # Fallback: try relative to this file
            default_path = Path(__file__).parent.parent / "workflow.yaml"
            if default_path.exists():
                return default_path
            raise FileNotFoundError(
                "No workflow configuration found. Checked:\n"
                "  1. AF_WORKFLOW_CONFIG environment variable\n"
                "  2. config/workflows.yaml\n"
                "  3. Package default agentic_fleet/workflow.yaml"
            ) from exc

    def _load_config(self) -> dict[str, Any]:
        """Load YAML configuration from resolved path."""
        with open(self.config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

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

    def create_from_yaml(self, workflow_id: str) -> Any:  # type: ignore[type-arg]
        """Create a workflow instance from YAML configuration.

        Args:
            workflow_id: The workflow identifier

        Returns:
            Workflow instance (type depends on factory function)

        Raises:
            ValueError: If workflow_id is not found or factory function doesn't exist
        """
        self.get_workflow_config(workflow_id)
        # Factory function would be called here once workflow.py is migrated
        # For now, this is a placeholder that maintains the interface
        raise NotImplementedError(
            "Workflow creation will be implemented after workflow.py migration"
        )

    def _build_collaboration_args(self, config: WorkflowConfig) -> dict[str, Any]:
        """Build arguments for collaboration workflow factory."""
        # Placeholder - full implementation depends on workflow.py structure
        return {}

    def _build_magentic_fleet_args(self, config: WorkflowConfig) -> dict[str, Any]:
        """Build arguments for magentic fleet workflow factory."""
        # Placeholder - full implementation depends on workflow.py structure
        return {}
