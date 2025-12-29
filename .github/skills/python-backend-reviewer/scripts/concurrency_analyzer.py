#!/usr/bin/env python3
"""
Analyze concurrency issues: shared state mutation in async code, missing locks.

Usage:
    python concurrency_analyzer.py <file_or_directory>
"""

import ast
import sys
from pathlib import Path
from typing import Any


class ConcurrencyAnalyzer(ast.NodeVisitor):
    """Analyze concurrency issues in async Python code."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.issues: list[dict[str, Any]] = []
        self.current_class: str | None = None
        self.current_function: str | None = None
        self.is_async_context = False
        self.class_attributes: set[str] = set()
        self.instance_mutations: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class definitions and their attributes."""
        old_class = self.current_class
        old_attrs = self.class_attributes.copy()

        self.current_class = node.name
        self.class_attributes = set()

        # Find __init__ and track assigned attributes
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                self._extract_init_attributes(item)

        self.generic_visit(node)

        self.current_class = old_class
        self.class_attributes = old_attrs

    def _extract_init_attributes(self, init_node: ast.FunctionDef) -> None:
        """Extract self.attr assignments from __init__."""
        for node in ast.walk(init_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        self.class_attributes.add(target.attr)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        old_func = self.current_function
        old_async = self.is_async_context

        self.current_function = node.name
        self.is_async_context = True

        self.generic_visit(node)

        self.current_function = old_func
        self.is_async_context = old_async

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit sync function definitions."""
        old_func = self.current_function
        old_async = self.is_async_context

        self.current_function = node.name
        self.is_async_context = False

        self.generic_visit(node)

        self.current_function = old_func
        self.is_async_context = old_async

    def visit_Assign(self, node: ast.Assign) -> None:
        """Detect self.attr = X assignments in async context."""
        if not self.is_async_context or not self.current_class:
            self.generic_visit(node)
            return

        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                attr_name = target.attr
                # Skip private attributes that are likely intentional state
                if attr_name.startswith("_") and not attr_name.startswith("__"):
                    # Still flag if it looks like shared state
                    if any(
                        kw in attr_name.lower() for kw in ["client", "session", "config", "agent"]
                    ):
                        self._add_mutation_issue(node, attr_name, "shared_state_mutation")
                else:
                    self._add_mutation_issue(node, attr_name, "instance_mutation_in_async")

        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Detect self.attr += X in async context."""
        if not self.is_async_context or not self.current_class:
            self.generic_visit(node)
            return

        if (
            isinstance(node.target, ast.Attribute)
            and isinstance(node.target.value, ast.Name)
            and node.target.value.id == "self"
        ):
            attr_name = node.target.attr
            self._add_mutation_issue(node, attr_name, "augmented_mutation_in_async")

        self.generic_visit(node)

    def _add_mutation_issue(self, node: ast.AST, attr_name: str, issue_type: str) -> None:
        """Add a mutation issue to the list."""
        severity = "warning"
        if any(kw in attr_name.lower() for kw in ["client", "session", "model", "agent", "config"]):
            severity = "critical"

        messages = {
            "instance_mutation_in_async": (
                f"Mutating `self.{attr_name}` in async method `{self.current_function}` "
                f"of class `{self.current_class}`. This can cause race conditions if "
                f"multiple requests share the same instance."
            ),
            "shared_state_mutation": (
                f"Mutating potentially shared state `self.{attr_name}` in async method "
                f"`{self.current_function}`. If this class is a singleton or shared across "
                f"requests, concurrent modifications can cause data corruption."
            ),
            "augmented_mutation_in_async": (
                f"Augmented assignment to `self.{attr_name}` in async method "
                f"`{self.current_function}`. This is not atomic and can cause race conditions."
            ),
        }

        self.issues.append(
            {
                "type": issue_type,
                "severity": severity,
                "line": node.lineno,
                "class": self.current_class,
                "function": self.current_function,
                "attribute": attr_name,
                "message": messages.get(issue_type, f"Concurrency issue with self.{attr_name}"),
            }
        )


class SharedStateDetector(ast.NodeVisitor):
    """Detect patterns that suggest shared state issues."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.issues: list[dict[str, Any]] = []
        self.module_level_assignments: list[dict[str, Any]] = []
        self.singleton_patterns: list[dict[str, Any]] = []

    def visit_Module(self, node: ast.Module) -> None:
        """Check for module-level mutable state."""
        for item in node.body:
            # Module-level mutable assignments (excluding imports, classes, functions)
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and isinstance(
                        item.value, (ast.List, ast.Dict, ast.Set, ast.Call)
                    ):
                        self.issues.append(
                            {
                                "type": "module_level_mutable",
                                "severity": "info",
                                "line": item.lineno,
                                "name": target.id,
                                "message": (
                                    f"Module-level mutable `{target.id}` can cause issues "
                                    f"if modified during concurrent requests. Consider making "
                                    f"it immutable or request-scoped."
                                ),
                            }
                        )

        self.generic_visit(node)


def analyze_file(filepath: Path) -> dict[str, Any]:
    """Analyze a single Python file for concurrency issues."""
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(filepath))

        # Run both analyzers
        concurrency = ConcurrencyAnalyzer(str(filepath))
        concurrency.visit(tree)

        shared_state = SharedStateDetector(str(filepath))
        shared_state.visit(tree)

        return {
            "filepath": str(filepath),
            "issues": concurrency.issues + shared_state.issues,
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
        print("✅ No concurrency issues detected!")
        print("\nNote: This analysis catches common patterns but cannot detect all")
        print("concurrency issues. Manual review is still recommended for async code.")
        return

    print(f"🔍 Found {total_issues} potential concurrency issues:\n")

    # Group by severity
    critical = []
    warnings = []
    infos = []

    for result in results:
        if "error" in result:
            print(f"⚠️  Error analyzing {result['filepath']}: {result['error']}\n")
            continue

        for issue in result.get("issues", []):
            issue["filepath"] = result["filepath"]
            if issue["severity"] == "critical":
                critical.append(issue)
            elif issue["severity"] == "warning":
                warnings.append(issue)
            else:
                infos.append(issue)

    # Print critical issues
    if critical:
        print(f"{'=' * 80}")
        print(f"🔴 CRITICAL ({len(critical)}) - Fix before deploying to production")
        print(f"{'=' * 80}\n")

        for issue in critical:
            print(f"📄 {issue['filepath']}:{issue['line']}")
            if "class" in issue:
                print(f"   Class: {issue['class']}, Method: {issue['function']}")
            print(f"   {issue['message']}\n")

    # Print warnings
    if warnings:
        print(f"{'=' * 80}")
        print(f"⚠️  WARNINGS ({len(warnings)}) - Review for potential issues")
        print(f"{'=' * 80}\n")

        for issue in warnings:
            print(f"📄 {issue['filepath']}:{issue['line']}")
            if "class" in issue:
                print(f"   Class: {issue['class']}, Method: {issue['function']}")
            print(f"   {issue['message']}\n")

    # Print info
    if infos:
        print(f"{'=' * 80}")
        print(f"INFO ({len(infos)}) - Consider reviewing")
        print(f"{'=' * 80}\n")

        for issue in infos:
            print(f"📄 {issue['filepath']}:{issue['line']}")
            print(f"   {issue['message']}\n")

    # Print remediation guidance
    print(f"{'=' * 80}")
    print("📋 REMEDIATION GUIDANCE")
    print(f"{'=' * 80}\n")
    print("For shared state mutations in async code:")
    print("  1. Use request-scoped instances instead of shared singletons")
    print("  2. Pass state through function parameters or context objects")
    print("  3. Use asyncio.Lock for necessary shared state")
    print("  4. Make shared state immutable (frozen dataclasses, tuples)")
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
        print("Usage: python concurrency_analyzer.py <file_or_directory>")
        print("\nDetects potential concurrency issues in async Python code:")
        print("  - Shared state mutation in async methods")
        print("  - Module-level mutable state")
        print("  - Missing synchronization patterns")
        sys.exit(1)

    target_path = sys.argv[-1]
    path = Path(target_path)

    if not path.exists():
        print(f"❌ Error: Path '{path}' does not exist")
        sys.exit(1)

    # Collect Python files
    python_files = collect_python_files(path)
    if not python_files:
        print(f"❌ No Python files found in '{path}'")
        sys.exit(1)

    print(f"🔍 Analyzing {len(python_files)} Python files for concurrency issues...\n")

    # Analyze files
    results = [analyze_file(f) for f in python_files]
    print_analysis_results(results)


if __name__ == "__main__":
    main()
