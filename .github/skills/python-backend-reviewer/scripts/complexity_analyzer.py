#!/usr/bin/env python3
"""
Analyze code complexity metrics: cyclomatic complexity, nesting depth, function length.

Usage:
    python complexity_analyzer.py <file_or_directory>
    python complexity_analyzer.py --max-complexity 10 --max-length 50 <file_or_directory>
"""

import ast
import sys
from pathlib import Path
from typing import Any


class ComplexityAnalyzer(ast.NodeVisitor):
    """Analyze complexity metrics for Python code."""

    def __init__(self, filepath: str, max_complexity: int = 10, max_length: int = 50):
        self.filepath = filepath
        self.max_complexity = max_complexity
        self.max_length = max_length
        self.issues: list[dict[str, Any]] = []
        self.current_function: str | None = None
        self.current_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions and check complexity."""
        self._analyze_function(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions and check complexity."""
        self._analyze_function(node, is_async=True)
        self.generic_visit(node)

    def _analyze_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool
    ) -> None:
        """Analyze a function for complexity issues."""
        func_name = node.name
        func_type = "async function" if is_async else "function"

        # Calculate cyclomatic complexity
        complexity = self._calculate_complexity(node)
        if complexity > self.max_complexity:
            self.issues.append(
                {
                    "type": "high_complexity",
                    "severity": "warning",
                    "line": node.lineno,
                    "function": func_name,
                    "complexity": complexity,
                    "message": (
                        f"{func_type.capitalize()} '{func_name}' has cyclomatic complexity of {complexity} "
                        f"(threshold: {self.max_complexity}). Consider breaking it into smaller functions."
                    ),
                }
            )

        # Calculate function length
        func_length = node.end_lineno - node.lineno + 1
        if func_length > self.max_length:
            self.issues.append(
                {
                    "type": "long_function",
                    "severity": "info",
                    "line": node.lineno,
                    "function": func_name,
                    "length": func_length,
                    "message": (
                        f"{func_type.capitalize()} '{func_name}' is {func_length} lines long "
                        f"(threshold: {self.max_length}). Consider breaking it into smaller functions."
                    ),
                }
            )

        # Check nesting depth
        max_depth = self._calculate_max_depth(node)
        if max_depth > 4:
            self.issues.append(
                {
                    "type": "deep_nesting",
                    "severity": "warning",
                    "line": node.lineno,
                    "function": func_name,
                    "depth": max_depth,
                    "message": (
                        f"{func_type.capitalize()} '{func_name}' has maximum nesting depth of {max_depth}. "
                        f"Consider extracting nested logic into separate functions."
                    ),
                }
            )

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a node."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Count decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Count and/or operators
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                # List/dict/set comprehensions with conditionals
                complexity += len(child.ifs)

        return complexity

    def _calculate_max_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of control structures."""
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            # Count nesting for control structures
            if isinstance(
                child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.With, ast.AsyncWith, ast.Try)
            ):
                child_max = self._calculate_max_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_max)
            else:
                child_max = self._calculate_max_depth(child, current_depth)
                max_depth = max(max_depth, child_max)

        return max_depth

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions and check for god classes."""
        method_count = sum(
            1 for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        )

        if method_count > 20:
            self.issues.append(
                {
                    "type": "god_class",
                    "severity": "warning",
                    "line": node.lineno,
                    "class": node.name,
                    "method_count": method_count,
                    "message": (
                        f"Class '{node.name}' has {method_count} methods. "
                        f"Consider splitting it into smaller, more focused classes."
                    ),
                }
            )

        self.generic_visit(node)


def analyze_file(filepath: Path, max_complexity: int = 10, max_length: int = 50) -> dict[str, Any]:
    """Analyze a single Python file for complexity issues."""
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(filepath))
        analyzer = ComplexityAnalyzer(str(filepath), max_complexity, max_length)
        analyzer.visit(tree)

        return {
            "filepath": str(filepath),
            "issues": analyzer.issues,
        }

    except (SyntaxError, UnicodeDecodeError) as e:
        return {
            "filepath": str(filepath),
            "error": str(e),
            "issues": [],
        }


def print_analysis_results(results: list[dict[str, Any]]) -> None:
    """Print analysis results in a readable format."""
    total_issues = sum(len(r.get("issues", [])) for r in results)

    if total_issues == 0:
        print("✅ No complexity issues found!")
        return

    print(f"🔍 Found {total_issues} complexity issues:\n")

    # Group by severity
    warnings = []
    infos = []

    for result in results:
        if "error" in result:
            print(f"⚠️  Error analyzing {result['filepath']}: {result['error']}\n")
            continue

        for issue in result.get("issues", []):
            issue["filepath"] = result["filepath"]
            if issue["severity"] == "warning":
                warnings.append(issue)
            else:
                infos.append(issue)

    # Print warnings
    if warnings:
        print(f"{'=' * 80}")
        print(f"⚠️  WARNINGS ({len(warnings)})")
        print(f"{'=' * 80}\n")

        for issue in warnings:
            print(f"📄 {issue['filepath']}:{issue['line']}")
            print(f"   {issue['message']}\n")

    # Print infos
    if infos:
        print(f"{'=' * 80}")
        print(f"INFO ({len(infos)})")
        print(f"{'=' * 80}\n")

        for issue in infos:
            print(f"📄 {issue['filepath']}:{issue['line']}")
            print(f"   {issue['message']}\n")


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
        print("Usage: python complexity_analyzer.py <file_or_directory>")
        print(
            "       python complexity_analyzer.py --max-complexity 10 --max-length 50 <file_or_directory>"
        )
        sys.exit(1)

    # Parse arguments
    max_complexity = 10
    max_length = 50
    target_path = sys.argv[-1]

    if "--max-complexity" in sys.argv:
        idx = sys.argv.index("--max-complexity")
        max_complexity = int(sys.argv[idx + 1])

    if "--max-length" in sys.argv:
        idx = sys.argv.index("--max-length")
        max_length = int(sys.argv[idx + 1])

    path = Path(target_path)
    if not path.exists():
        print(f"❌ Error: Path '{path}' does not exist")
        sys.exit(1)

    # Collect Python files
    python_files = collect_python_files(path)
    if not python_files:
        print(f"❌ No Python files found in '{path}'")
        sys.exit(1)

    print(f"🔍 Analyzing {len(python_files)} Python files...")
    print(f"   Max complexity: {max_complexity}, Max length: {max_length}\n")

    # Analyze files
    results = [analyze_file(f, max_complexity, max_length) for f in python_files]
    print_analysis_results(results)


if __name__ == "__main__":
    main()
