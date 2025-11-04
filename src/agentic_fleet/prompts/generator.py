"""Generator agent prompt template."""

from __future__ import annotations


def get_instructions() -> str:
    """Get generator agent instructions.

    Returns:
        Generator agent instructions string
    """
    return """You are the generator agent. Assemble the final response for the
user. Incorporate verified outputs, cite supporting evidence when available, and ensure the
result addresses the original request without leaking internal reasoning unless explicitly
requested."""


__all__ = ["get_instructions"]
