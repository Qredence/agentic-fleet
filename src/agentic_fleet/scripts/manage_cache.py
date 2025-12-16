#!/usr/bin/env python3
"""
Utility script to manage DSPy compiled module cache.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from agentic_fleet.utils.cfg import DEFAULT_CACHE_PATH


def clear_cache() -> None:
    """Clear the compiled module cache."""
    cache_file = Path(DEFAULT_CACHE_PATH)
    if cache_file.exists():
        cache_file.unlink()
        print(f"✓ Cleared cache: {cache_file}")
    else:
        print("No cache file found")


def show_cache_info() -> None:
    """Show information about cached module."""
    cache_file = Path(DEFAULT_CACHE_PATH)
    if cache_file.exists():
        size = cache_file.stat().st_size
        mtime = cache_file.stat().st_mtime
        from datetime import datetime

        modified = datetime.fromtimestamp(mtime).isoformat()
        print(f"Cache file: {cache_file}")
        print(f"Size: {size:,} bytes")
        print(f"Last modified: {modified}")
    else:
        print("No cache file found")


def main() -> None:
    """Run the cache management script."""
    parser = argparse.ArgumentParser(
        description="Manage DSPy compiled module cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --info    # Show cache information
  %(prog)s --clear   # Clear the cache
        """,
    )

    parser.add_argument("--info", action="store_true", help="Show cache information")
    parser.add_argument("--clear", action="store_true", help="Clear the cache")

    args = parser.parse_args()

    if args.clear:
        clear_cache()
    elif args.info:
        show_cache_info()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
