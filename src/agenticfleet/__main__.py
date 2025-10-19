"""
Entry point for running AgenticFleet as a module.

Usage:
    uv run python -m agenticfleet
"""

import sys


def main() -> None:
    """Main entry point for the AgenticFleet application."""
    # Initialize tracing before any agent operations
    try:
        from agenticfleet.observability import setup_tracing

        setup_tracing()
    except Exception:
        # Tracing is optional - continue if it fails
        pass

    from agenticfleet.cli.repl import run_repl_main

    sys.exit(run_repl_main())


if __name__ == "__main__":
    main()
