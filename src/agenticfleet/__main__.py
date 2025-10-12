"""
Entry point for running AgenticFleet as a module.

Usage:
    uv run python -m agenticfleet
"""

import sys


def main() -> None:
    """Main entry point for the AgenticFleet application."""
    from agenticfleet.cli.repl import run_repl_main

    sys.exit(run_repl_main())


if __name__ == "__main__":
    main()
