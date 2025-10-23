"""Validate AGENTS.md invariants across the repository.

This script is intended for automated + local enforcement of documentation and
lightweight semantic invariants described in the root `AGENTS.md` file.

It performs heuristic (best-effort) checks and reports:

1. Presence of required AGENTS.md files
2. Required sections / anchors in root AGENTS.md
3. Markdown formatting sanity (blank lines around tables heuristic)
4. Codebase scans for common anti‑patterns:
   - Hardcoded model_id strings in OpenAIResponsesClient(...) calls
   - Direct python / pytest invocations without `uv run` (in docs / AGENTS files)
5. Tool directory function signatures lacking return type annotations (basic regex)

Exit codes:
  0 = All checks passed (or only warnings when --no-strict)
  1 = One or more failures (in strict mode or by default)

Usage:
  uv run python tools/scripts/validate_agents_docs.py
  uv run python tools/scripts/validate_agents_docs.py --format json --strict

Intentionally avoids heavy parsing dependencies; uses stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_AGENT_FILES = [
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "src" / "agenticfleet" / "AGENTS.md",
    REPO_ROOT / "tests" / "AGENTS.md",
    REPO_ROOT / "src" / "frontend" / "AGENTS.md",
    REPO_ROOT / "src" / "agenticfleet" / "agents" / "AGENTS.md",
    REPO_ROOT / "src" / "agenticfleet" / "workflows" / "AGENTS.md",
]

ROOT_REQUIRED_SECTIONS = [
    "# AGENTS.md",  # top header
    "Invariants (DO NOT VIOLATE)",
    "Quick Command Reference",
]

MODEL_HARDCODE_PATTERN = re.compile(
    r"OpenAIResponsesClient\s*\(\s*model_id\s*=\s*['\"]gpt-[^'\"]+['\"]", re.IGNORECASE
)

DIRECT_PYTHON_CMD_PATTERN = re.compile(r"(?<!uv run )(python -m |pytest)\b")

# Matches function definitions (single or multi-line) lacking a return type annotation
# Uses a negated character class with fixed upper limit to prevent catastrophic backtracking
FUNCTION_DEF_NO_RETURN = re.compile(r"^def\s+\w+\s*\([^)]{0,500}\)\s*:(?!\s*->)", re.MULTILINE)

TABLE_HEADER_PATTERN = re.compile(r"^\|.+\|\s*$")

PY_TOOL_DIRS = [REPO_ROOT / "src" / "agenticfleet" / "agents"]


@dataclass
class Finding:
    category: str
    message: str
    file: str | None = None
    line: int | None = None
    severity: str = "error"  # error | warning | info

    def to_dict(self) -> dict:
        return asdict(self)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:  # pragma: no cover - defensive
        return f"<ERROR READING FILE: {e}>"


def check_required_files() -> list[Finding]:
    findings: list[Finding] = []
    for p in REQUIRED_AGENT_FILES:
        if not p.exists():
            findings.append(
                Finding(
                    category="files",
                    message=f"Missing required AGENTS doc: {p.relative_to(REPO_ROOT)}",
                    file=str(p),
                )
            )
    return findings


def check_root_sections() -> list[Finding]:
    root = REQUIRED_AGENT_FILES[0]
    text = read_text(root)
    findings: list[Finding] = []
    for sec in ROOT_REQUIRED_SECTIONS:
        if sec not in text:
            findings.append(
                Finding(
                    category="sections",
                    message=f"Root AGENTS.md missing required section marker: '{sec}'",
                    file=str(root),
                )
            )
    return findings


def check_markdown_table_spacing() -> list[Finding]:
    findings: list[Finding] = []
    for path in REQUIRED_AGENT_FILES:
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines):
            if TABLE_HEADER_PATTERN.match(line.strip()):
                # Check previous line blank
                prev_blank = idx == 0 or lines[idx - 1].strip() == ""
                # We'll only enforce preceding blank line (markdownlint MD058 heuristic)
                if not prev_blank:
                    findings.append(
                        Finding(
                            category="markdown",
                            message="Table header not preceded by blank line (MD058 heuristic)",
                            file=str(path),
                            line=idx + 1,
                            severity="warning",
                        )
                    )
    return findings


def scan_code_for_model_hardcodes() -> list[Finding]:
    findings: list[Finding] = []
    for py in REPO_ROOT.rglob("*.py"):
        # Skip virtual envs / node modules / dist
        rel = py.relative_to(REPO_ROOT)
        if any(part in rel.parts for part in (".venv", "node_modules", "dist")):
            continue
        text = read_text(py)
        for m in MODEL_HARDCODE_PATTERN.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            findings.append(
                Finding(
                    category="model-hardcode",
                    message=(
                        "Hardcoded model_id literal in OpenAIResponsesClient "
                        "(use YAML-driven config)"
                    ),
                    file=str(py),
                    line=line_no,
                )
            )
    return findings


def scan_docs_for_direct_python_cmds() -> list[Finding]:
    findings: list[Finding] = []
    doc_paths = [p for p in REPO_ROOT.rglob("*.md") if "node_modules" not in p.parts]
    for p in doc_paths:
        text = read_text(p)
        for m in DIRECT_PYTHON_CMD_PATTERN.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            snippet = text[m.start() : m.start() + 40].splitlines()[0]
            findings.append(
                Finding(
                    category="uv-run",
                    message=f"Direct python/pytest invocation without 'uv run': {snippet}",
                    file=str(p),
                    line=line_no,
                    severity="warning",
                )
            )
    return findings


def scan_tools_for_missing_return_types() -> list[Finding]:
    findings: list[Finding] = []
    for base in PY_TOOL_DIRS:
        if not base.exists():
            continue
        for py in base.rglob("*.py"):
            text = read_text(py)
            for idx, line in enumerate(text.splitlines()):
                if FUNCTION_DEF_NO_RETURN.match(line.strip()):
                    findings.append(
                        Finding(
                            category="typing",
                            message="Function missing return type annotation",
                            file=str(py),
                            line=idx + 1,
                            severity="warning",
                        )
                    )
    return findings


def aggregate_findings() -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_required_files())
    findings.extend(check_root_sections())
    findings.extend(check_markdown_table_spacing())
    findings.extend(scan_code_for_model_hardcodes())
    findings.extend(scan_docs_for_direct_python_cmds())
    findings.extend(scan_tools_for_missing_return_types())
    return findings


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate AGENTS.md invariants")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings as well as errors")
    args = parser.parse_args(list(argv) if argv is not None else None)

    findings = aggregate_findings()

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]

    exit_code = 0
    if errors or (args.strict and warnings):
        exit_code = 1

    if args.format == "json":
        payload = {
            "summary": {
                "errors": len(errors),
                "warnings": len(warnings),
                "total": len(findings),
                "strict": args.strict,
                "exit_code": exit_code,
            },
            "findings": [f.to_dict() for f in findings],
        }
        print(json.dumps(payload, indent=2))
    else:
        print("AGENTS Invariant Validation Report")
        print("=" * 38)
        print(f"Errors  : {len(errors)}")
        print(f"Warnings: {len(warnings)}")
        print(f"Total   : {len(findings)}\n")
        for f in findings:
            loc = f"{f.file}:{f.line}" if f.file and f.line else (f.file or "<n/a>")
            print(f"[{f.severity.upper():7}] {f.category:15} {loc} - {f.message}")
        if exit_code == 0:
            print("\nAll invariants satisfied (or only warnings in non-strict mode).")
        else:
            print("\nInvariant violations detected.")
            if warnings and not errors and args.strict:
                print("(Strict mode: warnings treated as errors)")
    return exit_code


if __name__ == "__main__":  # pragma: no cover - entry point
    sys.exit(main())
