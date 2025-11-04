#!/usr/bin/env python3
"""Automated code quality feedback tool.

This script analyzes Python code and provides automated feedback on:
- Code quality and best practices
- Potential bugs or security issues
- Performance considerations
- Type safety and documentation
- Testing coverage

Usage:
    python tools/scripts/automated_feedback.py [--file FILE | --dir DIR] [--format FORMAT]

Examples:
    # Analyze a single file
    python tools/scripts/automated_feedback.py --file src/agentic_fleet/api/chat/service.py

    # Analyze a directory
    python tools/scripts/automated_feedback.py --dir src/agentic_fleet/api

    # Output as JSON
    python tools/scripts/automated_feedback.py --dir src --format json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FeedbackItem:
    """Represents a single feedback item."""
    
    category: str  # 'quality', 'security', 'performance', 'documentation', 'testing'
    severity: str  # 'error', 'warning', 'info'
    message: str
    file: str
    line: int | None = None
    suggestion: str | None = None


@dataclass
class AnalysisResult:
    """Results of code analysis."""
    
    file: str
    feedback: list[FeedbackItem] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


class CodeAnalyzer:
    """Analyzes Python code for quality, security, and best practices."""
    
    def __init__(self) -> None:
        self.results: list[AnalysisResult] = []
    
    def analyze_file(self, file_path: Path) -> AnalysisResult:
        """Analyze a single Python file."""
        result = AnalysisResult(file=str(file_path))
        
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
            
            # Run various checks
            self._check_docstrings(tree, content, result)
            self._check_type_hints(tree, result)
            self._check_error_handling(tree, result)
            self._check_security_patterns(content, result)
            self._check_performance_patterns(tree, content, result)
            self._calculate_metrics(tree, content, result)
            
        except SyntaxError as e:
            result.feedback.append(
                FeedbackItem(
                    category="quality",
                    severity="error",
                    message=f"Syntax error: {e.msg}",
                    file=str(file_path),
                    line=e.lineno,
                )
            )
        except Exception as e:
            result.feedback.append(
                FeedbackItem(
                    category="quality",
                    severity="error",
                    message=f"Failed to analyze file: {e}",
                    file=str(file_path),
                )
            )
        
        self.results.append(result)
        return result
    
    def _check_docstrings(
        self, tree: ast.AST, content: str, result: AnalysisResult
    ) -> None:
        """Check for missing or inadequate docstrings."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Skip private functions/classes unless they're __init__ or __main__
                if node.name.startswith("_") and node.name not in ("__init__", "__main__"):
                    continue
                
                docstring = ast.get_docstring(node)
                if not docstring:
                    result.feedback.append(
                        FeedbackItem(
                            category="documentation",
                            severity="warning",
                            message=f"Missing docstring for {node.__class__.__name__} '{node.name}'",
                            file=result.file,
                            line=node.lineno,
                            suggestion="Add a docstring describing the purpose, parameters, and return value",
                        )
                    )
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.args.args and "Args:" not in docstring:
                    # Check if function has parameters but docstring doesn't mention Args
                    result.feedback.append(
                        FeedbackItem(
                            category="documentation",
                            severity="info",
                            message=f"Function '{node.name}' has parameters but docstring doesn't document them",
                            file=result.file,
                            line=node.lineno,
                            suggestion="Add an 'Args:' section to document parameters",
                        )
                    )
    
    def _check_type_hints(self, tree: ast.AST, result: AnalysisResult) -> None:
        """Check for missing type hints."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private functions and special methods
                if node.name.startswith("_") and not node.name.startswith("__"):
                    continue
                
                # Check return type annotation
                if node.returns is None and node.name not in ("__init__",):
                    result.feedback.append(
                        FeedbackItem(
                            category="quality",
                            severity="warning",
                            message=f"Function '{node.name}' missing return type annotation",
                            file=result.file,
                            line=node.lineno,
                            suggestion="Add '-> ReturnType' annotation",
                        )
                    )
                
                # Check parameter type annotations
                for arg in node.args.args:
                    if arg.annotation is None and arg.arg not in ("self", "cls"):
                        result.feedback.append(
                            FeedbackItem(
                                category="quality",
                                severity="warning",
                                message=f"Parameter '{arg.arg}' in function '{node.name}' missing type annotation",
                                file=result.file,
                                line=node.lineno,
                                suggestion=f"Add type annotation: '{arg.arg}: ParamType'",
                            )
                        )
    
    def _check_error_handling(self, tree: ast.AST, result: AnalysisResult) -> None:
        """Check error handling patterns."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Check for bare except
                if node.type is None:
                    result.feedback.append(
                        FeedbackItem(
                            category="quality",
                            severity="error",
                            message="Bare 'except:' catches all exceptions (including KeyboardInterrupt)",
                            file=result.file,
                            line=node.lineno,
                            suggestion="Specify exception type: 'except ExceptionType:'",
                        )
                    )
                
                # Check for too broad exception handling
                if isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    result.feedback.append(
                        FeedbackItem(
                            category="quality",
                            severity="warning",
                            message="Catching 'Exception' is too broad",
                            file=result.file,
                            line=node.lineno,
                            suggestion="Use more specific exception types",
                        )
                    )
    
    def _check_security_patterns(self, content: str, result: AnalysisResult) -> None:
        """Check for common security issues."""
        lines = content.split("\n")
        
        # Check for hardcoded secrets
        secret_patterns = [
            (r'api[_-]?key\s*=\s*["\'][\w-]{20,}["\']', "API key"),
            (r'password\s*=\s*["\'][^"\']+["\']', "password"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "secret"),
            (r'token\s*=\s*["\'][\w-]{20,}["\']', "token"),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, secret_type in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    result.feedback.append(
                        FeedbackItem(
                            category="security",
                            severity="error",
                            message=f"Possible hardcoded {secret_type} detected",
                            file=result.file,
                            line=i,
                            suggestion="Use environment variables or secrets management",
                        )
                    )
        
        # Check for SQL injection vulnerabilities
        if re.search(r'execute\([^,]+\s*%\s*', content) or re.search(r'execute\([^,]+\s*\+\s*', content):
            result.feedback.append(
                FeedbackItem(
                    category="security",
                    severity="error",
                    message="Potential SQL injection vulnerability detected",
                    file=result.file,
                    suggestion="Use parameterized queries or ORM",
                )
            )
        
        # Check for shell injection
        if "os.system(" in content or "subprocess.call(" in content:
            result.feedback.append(
                FeedbackItem(
                    category="security",
                    severity="warning",
                    message="Potential shell injection risk with os.system() or subprocess.call()",
                    file=result.file,
                    suggestion="Use subprocess.run() with shell=False and list arguments",
                )
            )
    
    def _check_performance_patterns(
        self, tree: ast.AST, content: str, result: AnalysisResult
    ) -> None:
        """Check for performance issues."""
        # Check for inefficient string concatenation in loops
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add) and isinstance(child.target, ast.Name):
                        result.feedback.append(
                            FeedbackItem(
                                category="performance",
                                severity="info",
                                message="String concatenation in loop may be inefficient",
                                file=result.file,
                                line=node.lineno,
                                suggestion="Consider using ''.join() or a list comprehension",
                            )
                        )
    
    def _calculate_metrics(
        self, tree: ast.AST, content: str, result: AnalysisResult
    ) -> None:
        """Calculate code metrics."""
        lines = content.split("\n")
        
        # Count various elements
        functions = sum(1 for _ in ast.walk(tree) if isinstance(_, (ast.FunctionDef, ast.AsyncFunctionDef)))
        classes = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.ClassDef))
        
        # Calculate complexity metrics
        result.metrics = {
            "total_lines": len(lines),
            "code_lines": len([line for line in lines if line.strip() and not line.strip().startswith("#")]),
            "comment_lines": len([line for line in lines if line.strip().startswith("#")]),
            "functions": functions,
            "classes": classes,
        }
    
    def analyze_directory(self, directory: Path, recursive: bool = True) -> list[AnalysisResult]:
        """Analyze all Python files in a directory."""
        pattern = "**/*.py" if recursive else "*.py"
        
        for file_path in directory.glob(pattern):
            # Skip __pycache__ and virtual environments
            if "__pycache__" in str(file_path) or ".venv" in str(file_path):
                continue
            
            self.analyze_file(file_path)
        
        return self.results
    
    def print_report(self, output_format: str = "text") -> None:
        """Print analysis report."""
        if output_format == "json":
            self._print_json_report()
        else:
            self._print_text_report()
    
    def _print_text_report(self) -> None:
        """Print report in text format."""
        print("=" * 80)
        print("AUTOMATED CODE QUALITY FEEDBACK")
        print("=" * 80)
        print()
        
        # Group feedback by severity
        errors = []
        warnings = []
        info = []
        
        for result in self.results:
            for item in result.feedback:
                if item.severity == "error":
                    errors.append(item)
                elif item.severity == "warning":
                    warnings.append(item)
                else:
                    info.append(item)
        
        # Print summary
        print(f"Files analyzed: {len(self.results)}")
        print(f"Total issues: {len(errors) + len(warnings) + len(info)}")
        print(f"  - Errors: {len(errors)}")
        print(f"  - Warnings: {len(warnings)}")
        print(f"  - Info: {len(info)}")
        print()
        
        # Print issues by severity
        if errors:
            print("ERRORS")
            print("-" * 80)
            for item in errors:
                self._print_feedback_item(item)
            print()
        
        if warnings:
            print("WARNINGS")
            print("-" * 80)
            for item in warnings:
                self._print_feedback_item(item)
            print()
        
        if info:
            print("INFO")
            print("-" * 80)
            for item in info:
                self._print_feedback_item(item)
            print()
        
        # Print metrics summary
        if self.results:
            print("CODE METRICS")
            print("-" * 80)
            total_lines = sum(r.metrics.get("total_lines", 0) for r in self.results)
            total_functions = sum(r.metrics.get("functions", 0) for r in self.results)
            total_classes = sum(r.metrics.get("classes", 0) for r in self.results)
            
            print(f"Total lines of code: {total_lines}")
            print(f"Total functions: {total_functions}")
            print(f"Total classes: {total_classes}")
            print()
    
    def _print_feedback_item(self, item: FeedbackItem) -> None:
        """Print a single feedback item."""
        location = f"{item.file}:{item.line}" if item.line else item.file
        print(f"[{item.category.upper()}] {location}")
        print(f"  {item.message}")
        if item.suggestion:
            print(f"  Suggestion: {item.suggestion}")
        print()
    
    def _print_json_report(self) -> None:
        """Print report in JSON format."""
        output = {
            "summary": {
                "files_analyzed": len(self.results),
                "total_issues": sum(len(r.feedback) for r in self.results),
                "errors": sum(
                    1 for r in self.results for f in r.feedback if f.severity == "error"
                ),
                "warnings": sum(
                    1 for r in self.results for f in r.feedback if f.severity == "warning"
                ),
                "info": sum(
                    1 for r in self.results for f in r.feedback if f.severity == "info"
                ),
            },
            "results": [
                {
                    "file": r.file,
                    "feedback": [
                        {
                            "category": f.category,
                            "severity": f.severity,
                            "message": f.message,
                            "line": f.line,
                            "suggestion": f.suggestion,
                        }
                        for f in r.feedback
                    ],
                    "metrics": r.metrics,
                }
                for r in self.results
            ],
        }
        print(json.dumps(output, indent=2))


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated code quality feedback tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Analyze a single file",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        help="Analyze all files in a directory",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't analyze directories recursively",
    )
    
    args = parser.parse_args()
    
    if not args.file and not args.dir:
        parser.error("Either --file or --dir must be specified")
    
    analyzer = CodeAnalyzer()
    
    if args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            return 1
        analyzer.analyze_file(args.file)
    elif args.dir:
        if not args.dir.exists():
            print(f"Error: Directory not found: {args.dir}", file=sys.stderr)
            return 1
        analyzer.analyze_directory(args.dir, recursive=not args.no_recursive)
    
    analyzer.print_report(output_format=args.format)
    
    # Return non-zero if errors were found
    errors = sum(
        1 for r in analyzer.results for f in r.feedback if f.severity == "error"
    )
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
