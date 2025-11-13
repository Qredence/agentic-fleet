"""Workflow configuration Pydantic models."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReasoningConfig(BaseModel):
    """Optional reasoning configuration for a workflow manager."""

    model_config = ConfigDict(extra="allow")

    effort: str | None = None
    verbosity: str | None = None


class WorkflowManagerConfig(BaseModel):
    """Configuration for the workflow manager agent."""

    model_config = ConfigDict(extra="allow")

    model: str
    instructions: str | None = None
    reasoning: ReasoningConfig | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    store: bool | None = None
    max_round_count: int | None = None
    max_stall_count: int | None = None
    max_reset_count: int | None = None

    def get(
        self, key: str, default: Any | None = None
    ) -> Any | None:  # pragma: no cover - trivial accessor
        """Dictionary-style accessor for compatibility with legacy code paths."""

        try:
            data = self.model_dump()
        except AttributeError:  # Pydantic v1 fallback
            data = self.dict()
        return data.get(key, default)


class WorkflowConfig(BaseModel):
    """Validated workflow configuration entry."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    description: str = ""
    factory: str
    agents: dict[str, Any] = Field(default_factory=lambda: {})
    manager: WorkflowManagerConfig | dict[str, Any] = Field(default_factory=lambda: {})
    fleet: dict[str, Any] | None = None
    checkpointing: dict[str, Any] | bool | None = None
    approval: dict[str, Any] | bool | None = None
    cache: dict[str, Any] | bool | None = None
    agent_config_registry: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Backward compatibility helpers
    # ------------------------------------------------------------------
    def _manager_as_dict(self) -> dict[str, Any]:
        if isinstance(self.manager, WorkflowManagerConfig):
            try:
                return self.manager.model_dump()
            except AttributeError:  # pragma: no cover - Pydantic v1 fallback
                return self.manager.dict()
        return dict(self.manager)

    @property
    def orchestrator(self) -> dict[str, Any]:  # pragma: no cover - trivial accessor
        """Legacy alias for manager config.

        Older tests referenced ``config.orchestrator``. We expose a dict
        representation of the manager config to keep those tests passing.
        """
        return self._manager_as_dict()

    # Pydantic v1 compatibility: provide ``model_dump`` when unavailable so
    # tests expecting v2 semantics (flattened nested models) continue to work.
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:  # Prefer native implementation if present
            return super().model_dump(*args, **kwargs)
        except AttributeError:  # v1 fallback
            return self.dict(*args, **kwargs)
