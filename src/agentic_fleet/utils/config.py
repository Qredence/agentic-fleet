"""Configuration management utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentic_fleet.utils.factory import WorkflowFactory


class ConfigManager:
    """Manages configuration loading and resolution."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize config manager.

        Args:
            config_path: Optional explicit config path
        """
        self.workflow_factory = WorkflowFactory(config_path)

    def get_workflow_config(self, workflow_id: str) -> Any:
        """Get workflow configuration.

        Args:
            workflow_id: Workflow identifier

        Returns:
            WorkflowConfig instance
        """
        return self.workflow_factory.get_workflow_config(workflow_id)

    def list_workflows(self) -> list[dict[str, Any]]:
        """List available workflows.

        Returns:
            List of workflow metadata dictionaries
        """
        return self.workflow_factory.list_available_workflows()
