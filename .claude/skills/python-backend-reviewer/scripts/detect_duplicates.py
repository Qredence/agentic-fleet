#!/usr/bin/env python3
"""
Detect duplicate code blocks in Python files using AST analysis.

Usage:
    python detect_duplicates.py <file_or_directory>
    python detect_duplicates.py --threshold 0.8 <file_or_directory>
"""

import ast
import hashlib
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


class CodeBlockExtractor(ast.NodeVisitor):
    """Extract code blocks (functions, classes, methods) from AST."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.blocks: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        code = ast.unparse(node)
        self.blocks.append(
            {
                "type": "function",
                "name": node.name,
                "lineno": node.lineno,
                "code": code,
                "hash": self._hash_code(code),
                "filepath": self.filepath,
            }
        )
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        code = ast.unparse(node)
        self.blocks.append(
            {
                "type": "async_function",
                "name": node.name,
                "lineno": node.lineno,
                "code": code,
                "hash": self._hash_code(code),
                "filepath": self.filepath,
            }
        )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions."""
        code = ast.unparse(node)
        self.blocks.append(
            {
                "type": "class",
                "name": node.name,
                "lineno": node.lineno,
                "code": code,
                "hash": self._hash_code(code),
                "filepath": self.filepath,
            }
        )
        self.generic_visit(node)

    @staticmethod
    def _hash_code(code: str) -> str:
        """Generate hash of normalized code."""
        # Normalize whitespace for comparison
        normalized = " ".join(code.split())
        return hashlib.md5(normalized.encode()).hexdigest()


def find_duplicates(paths: list[Path], min_lines: int = 5) -> dict[str, list[dict]]:
    """
    Find duplicate code blocks across files.

    Args:
        paths: List of Python file paths to analyze
        min_lines: Minimum lines for a block to be considered (default: 5)

    Returns:
        Dictionary mapping hash to list of duplicate blocks
    """
    hash_map: dict[str, list[dict]] = defaultdict(list)

    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source, filename=str(path))
            extractor = CodeBlockExtractor(str(path))
            extractor.visit(tree)

            for block in extractor.blocks:
                # Filter out small blocks
                if block["code"].count("\n") >= min_lines:
                    hash_map[block["hash"]].append(block)

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"⚠️  Skipping {path}: {e}", file=sys.stderr)
            continue

    # Keep only hashes with duplicates
    return {h: blocks for h, blocks in hash_map.items() if len(blocks) > 1}


def print_duplicates(duplicates: dict[str, list[dict]]) -> None:
    """Print duplicate code blocks in a readable format."""
    if not duplicates:
        print("✅ No duplicate code blocks found!")
        return

    print(f"🔍 Found {len(duplicates)} sets of duplicate code blocks:\n")

    for i, (_code_hash, blocks) in enumerate(duplicates.items(), 1):
        print(f"{'=' * 80}")
        print(f"Duplicate Set #{i} ({len(blocks)} occurrences)")
        print(f"{'=' * 80}")

        for block in blocks:
            print(f"\n📄 {block['filepath']}:{block['lineno']}")
            print(f"   Type: {block['type']}, Name: {block['name']}")

        # Show code sample from first occurrence
        print("\n📝 Code sample:")
        code_lines = blocks[0]["code"].split("\n")
        for line in code_lines[:10]:  # Show first 10 lines
            print(f"   {line}")
        if len(code_lines) > 10:
            print(f"   ... ({len(code_lines) - 10} more lines)")

        print()


def collect_python_files(path: Path) -> list[Path]:
    """Recursively collect all Python files from a path."""
    if path.is_file() and path.suffix == ".py":
        return [path]
    elif path.is_dir():
        return list(path.rglob("*.py"))
    else:
        return []


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python detect_duplicates.py <file_or_directory>")
        print("       python detect_duplicates.py --min-lines 10 <file_or_directory>")
        sys.exit(1)

    # Parse arguments
    min_lines = 5
    target_path = sys.argv[-1]

    if "--min-lines" in sys.argv:
        idx = sys.argv.index("--min-lines")
        min_lines = int(sys.argv[idx + 1])

    path = Path(target_path)
    if not path.exists():
        print(f"❌ Error: Path '{path}' does not exist")
        sys.exit(1)

    # Collect Python files
    python_files = collect_python_files(path)
    if not python_files:
        print(f"❌ No Python files found in '{path}'")
        sys.exit(1)

    print(f"🔍 Analyzing {len(python_files)} Python files...\n")

    # Find and print duplicates
    duplicates = find_duplicates(python_files, min_lines=min_lines)
    print_duplicates(duplicates)

    # Exit with appropriate code
    sys.exit(0 if not duplicates else 1)


if __name__ == "__main__":
    main()
