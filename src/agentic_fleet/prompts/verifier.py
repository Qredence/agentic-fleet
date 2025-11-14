"""Verifier agent prompt template."""

from __future__ import annotations


def get_instructions() -> str:
    """Get verifier agent instructions.

    Returns:
        Verifier agent instructions string
    """
    return """You are the verifier agent. Inspect the current state, outputs, and
assumptions. Confirm whether the work satisfies requirements, highlight defects or missing
information, and suggest concrete follow-up actions."""


__all__ = ["get_instructions"]
