"""Helper functions for agent coordination and creation."""

from __future__ import annotations

import inspect
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

try:
    from agent_framework.openai import OpenAIResponsesClient as _PreferredOpenAIClient

    _RESPONSES_CLIENT_AVAILABLE = True
except ImportError:
    from agent_framework.openai import OpenAIChatClient as _PreferredOpenAIClient  # type: ignore

    _RESPONSES_CLIENT_AVAILABLE = False


def prepare_kwargs_for_client(client_cls: type, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Prepare kwargs for OpenAI client initialization by filtering to allowed parameters.

    Args:
        client_cls: The client class to prepare kwargs for.
        kwargs: Raw kwargs dictionary.

    Returns:
        Filtered kwargs dictionary containing only parameters accepted by the client class.
    """
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


def create_openai_client(**kwargs: Any) -> Any:
    """Create an OpenAI client instance with appropriate fallback handling.

    Args:
        **kwargs: Keyword arguments to pass to the client constructor.

    Returns:
        OpenAI client instance (OpenAIResponsesClient or OpenAIChatClient fallback).
    """
    client_kwargs = prepare_kwargs_for_client(_PreferredOpenAIClient, kwargs)
    if not _RESPONSES_CLIENT_AVAILABLE and not getattr(create_openai_client, "_fallback_warning_emitted", False):
        logger.warning(
            "OpenAIResponsesClient is unavailable; falling back to OpenAIChatClient (Responses API features disabled).",
        )
        create_openai_client._fallback_warning_emitted = True
    return _PreferredOpenAIClient(**client_kwargs)


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


@lru_cache(maxsize=1)
def get_default_agent_metadata() -> tuple[dict[str, Any], ...]:
    """Get metadata for default agents without instantiating them.

    Returns:
        Tuple of agent metadata dictionaries (tuple for hashability with lru_cache).
    """
    return (
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
    )


def resolve_workflow_config_path(config_path: str | Path | None = None) -> Path:
    """Resolve the workflow configuration path.

    Args:
        config_path: Optional override for the workflow config location.

    Returns:
        Path to the workflow configuration file.

    Raises:
        FileNotFoundError: If the config file cannot be located.
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
