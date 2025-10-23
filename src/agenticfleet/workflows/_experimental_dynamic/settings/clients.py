"""Helpers for constructing chat clients used in the dynamic workflow."""

from __future__ import annotations

from typing import Any

from agent_framework.openai import OpenAIResponsesClient

from agenticfleet.config import settings
from agenticfleet.core.exceptions import AgentConfigurationError
from agenticfleet.core.logging import get_logger
from agenticfleet.core.openai import get_responses_model_parameter

logger = get_logger(__name__)

TOOL_MODEL_FALLBACK = "gpt-4.1-mini"


def default_model_name() -> str:
    """Return the default responses model for agent participants."""
    workflow_defaults = settings.workflow_config.get("defaults", {}) or {}
    model = workflow_defaults.get("model") or settings.openai_model
    if not isinstance(model, str) or not model:
        raise AgentConfigurationError(
            "No default model configured. Set defaults.model in workflow.yaml or OPENAI_MODEL."
        )
    return model


def tool_model_name() -> str:
    """Return a model identifier suitable for hosted tool participants."""
    workflow_defaults = settings.workflow_config.get("defaults", {}) or {}
    model = workflow_defaults.get("tool_model")
    if isinstance(model, str) and model:
        return model
    return TOOL_MODEL_FALLBACK


def make_responses_client(model: str | None = None, **kwargs: Any) -> OpenAIResponsesClient:
    """Instantiate an OpenAIResponsesClient for creating chat agents."""
    selected_model = model or default_model_name()
    param_name = get_responses_model_parameter(OpenAIResponsesClient)
    client_kwargs: dict[str, Any] = {param_name: selected_model}

    if settings.openai_api_key:
        client_kwargs["api_key"] = settings.openai_api_key

    client_kwargs.update(kwargs)
    logger.debug("Creating OpenAIResponsesClient for model %s", selected_model)
    return OpenAIResponsesClient(**client_kwargs)


__all__ = ["default_model_name", "make_responses_client", "tool_model_name"]
