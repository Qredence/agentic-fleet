"""CLI module for AgenticFleet."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agenticfleet.cli.repl import main, run_repl_main

__all__ = ["main", "run_repl_main"]


def __getattr__(name: str) -> Any:
    """Lazy import to avoid circular dependencies."""
    if name in __all__:
        from agenticfleet.cli.repl import main, run_repl_main

        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
