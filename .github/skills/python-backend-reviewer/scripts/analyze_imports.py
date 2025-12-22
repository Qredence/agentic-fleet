#!/usr/bin/env python3
"""
Analyze imports and detect recreated utility functions that should be imports.

Usage:
    python analyze_imports.py <file_or_directory>
    python analyze_imports.py --check-utils <file_or_directory>
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


class ImportAnalyzer(ast.NodeVisitor):
    """Analyze imports and function definitions in Python files."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.imports: list[dict[str, Any]] = []
        self.functions: list[dict[str, Any]] = []
        self.issues: list[dict[str, Any]] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements."""
        for alias in node.names:
            self.imports.append(
                {
                    "type": "import",
                    "module": alias.name,
                    "alias": alias.asname,
                    "lineno": node.lineno,
                }
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from...import statements."""
        for alias in node.names:
            self.imports.append(
                {
                    "type": "from_import",
                    "module": node.module or "",
                    "name": alias.name,
                    "alias": alias.asname,
                    "lineno": node.lineno,
                }
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        self.functions.append(
            {
                "name": node.name,
                "lineno": node.lineno,
                "args": [arg.arg for arg in node.args.args],
                "is_async": False,
            }
        )
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        self.functions.append(
            {
                "name": node.name,
                "lineno": node.lineno,
                "args": [arg.arg for arg in node.args.args],
                "is_async": True,
            }
        )
        self.generic_visit(node)


# Common utility function patterns that should be imported
COMMON_UTILS = {
    "json_serialize": ["json.dumps", "json.loads", "orjson", "msgpack"],
    "date_format": ["datetime.strftime", "datetime.strptime", "dateutil"],
    "retry_logic": ["tenacity", "backoff", "retry decorator"],
    "validation": ["pydantic", "marshmallow", "cerberus", "voluptuous"],
    "logging_setup": ["logging.getLogger", "structlog", "loguru"],
    "http_client": ["requests", "httpx", "aiohttp"],
    "env_config": ["os.environ", "python-dotenv", "pydantic-settings"],
    "file_io": ["pathlib.Path", "open with context manager"],
    "async_utils": ["asyncio gather", "asyncio create_task"],
    "string_utils": ["strip/split/join", "str.format", "f-strings"],
}


def check_import_organization(analyzer: ImportAnalyzer) -> list[dict[str, Any]]:
    """Check for import organization issues."""
    issues = []

    # Check for relative imports in non-package context
    for imp in analyzer.imports:
        if imp["type"] == "from_import" and imp["module"].startswith("."):
            issues.append(
                {
                    "type": "relative_import",
                    "severity": "info",
                    "line": imp["lineno"],
                    "message": f"Relative import found: from {imp['module']} import {imp['name']}",
                }
            )

    # Check for wildcard imports
    for imp in analyzer.imports:
        if imp["type"] == "from_import" and imp["name"] == "*":
            issues.append(
                {
                    "type": "wildcard_import",
                    "severity": "warning",
                    "line": imp["lineno"],
                    "message": f"Wildcard import found: from {imp['module']} import *",
                }
            )

    # Check for unused imports (simplified check)
    # This is a basic heuristic - full analysis would require scope analysis
    imported_names = set()
    for imp in analyzer.imports:
        if imp["type"] == "import":
            name = imp["alias"] or imp["module"].split(".")[0]
            imported_names.add(name)
        elif imp["type"] == "from_import":
            name = imp["alias"] or imp["name"]
            imported_names.add(name)

    return issues


def detect_utility_reimplementation(analyzer: ImportAnalyzer) -> list[dict[str, Any]]:
    """Detect functions that look like reimplemented utilities."""
    issues = []

    # Common patterns that suggest utility reimplementation
    utility_patterns = {
        "serialize": ["serialize", "to_json", "to_dict", "dump"],
        "deserialize": ["deserialize", "from_json", "from_dict", "load"],
        "validate": ["validate", "check", "verify", "ensure"],
        "retry": ["retry", "attempt", "with_retry"],
        "log": ["log_", "logger", "write_log"],
        "parse": ["parse_", "extract_", "get_from"],
        "format": ["format_", "pretty", "stringify"],
    }

    for func in analyzer.functions:
        func_name_lower = func["name"].lower()

        for category, patterns in utility_patterns.items():
            if any(pattern in func_name_lower for pattern in patterns):
                issues.append(
                    {
                        "type": "potential_utility_reimplementation",
                        "severity": "info",
                        "line": func["lineno"],
                        "category": category,
                        "function": func["name"],
                        "message": (
                            f"Function '{func['name']}' may be reimplementing a common utility. "
                            f"Consider using existing libraries: {', '.join(COMMON_UTILS.get(category, ['standard library']))}"
                        ),
                    }
                )

    return issues


def analyze_file(filepath: Path) -> dict[str, Any]:
    """Analyze a single Python file for import and utility issues."""
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(filepath))
        analyzer = ImportAnalyzer(str(filepath))
        analyzer.visit(tree)

        import_issues = check_import_organization(analyzer)
        utility_issues = detect_utility_reimplementation(analyzer)

        return {
            "filepath": str(filepath),
            "imports_count": len(analyzer.imports),
            "functions_count": len(analyzer.functions),
            "issues": import_issues + utility_issues,
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
        print("✅ No import or utility issues found!")
        return

    print(f"🔍 Found {total_issues} potential issues:\n")

    # Group issues by severity
    by_severity: dict[str, list[dict]] = defaultdict(list)

    for result in results:
        if "error" in result:
            print(f"⚠️  Error analyzing {result['filepath']}: {result['error']}\n")
            continue

        for issue in result.get("issues", []):
            issue["filepath"] = result["filepath"]
            by_severity[issue["severity"]].append(issue)

    # Print warnings first
    if "warning" in by_severity:
        print(f"{'=' * 80}")
        print(f"⚠️  WARNINGS ({len(by_severity['warning'])})")
        print(f"{'=' * 80}\n")

        for issue in by_severity["warning"]:
            print(f"📄 {issue['filepath']}:{issue['line']}")
            print(f"   {issue['message']}\n")

    # Then info
    if "info" in by_severity:
        print(f"{'=' * 80}")
        print(f"INFO ({len(by_severity['info'])})")
        print(f"{'=' * 80}\n")

        for issue in by_severity["info"]:
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
        print("Usage: python analyze_imports.py <file_or_directory>")
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

    print(f"🔍 Analyzing {len(python_files)} Python files...\n")

    # Analyze files
    results = [analyze_file(f) for f in python_files]
    print_analysis_results(results)


if __name__ == "__main__":
    main()
