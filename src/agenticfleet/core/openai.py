"""Helpers for working with OpenAI clients used across AgenticFleet."""

from __future__ import annotations

import inspect


def get_responses_model_parameter(client_cls: type[object]) -> str:
    """Return the parameter name used for the responses model on the client."""

    try:
        signature = inspect.signature(client_cls.__init__)  # type: ignore[attr-defined]
    except (TypeError, ValueError):
        return "model"

    parameters = signature.parameters

    if "model_id" in parameters:
        return "model"

    if "model" in parameters:
        return "model"

    for parameter in parameters.values():
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            return "model"

    return "model_id"


__all__ = ["get_responses_model_parameter"]
