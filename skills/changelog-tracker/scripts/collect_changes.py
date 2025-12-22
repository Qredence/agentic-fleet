#!/usr/bin/env python3
"""Collect changelog inputs from git history and file paths.

Outputs a concise, human-readable summary grouped by area.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def _try_run(cmd: list[str]) -> str | None:
    try:
        return _run(cmd)
    except subprocess.CalledProcessError:
        return None


def _repo_root() -> Path:
    root = _run(["git", "rev-parse", "--show-toplevel"])
    return Path(root)


def _latest_tag() -> str | None:
    return _try_run(["git", "describe", "--tags", "--abbrev=0"])


def _read_version(pyproject_path: Path) -> str | None:
    try:
        import tomllib
    except Exception:
        return None
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    project = data.get("project", {})
    version = project.get("version")
    if isinstance(version, str) and version.strip():
        return version.strip()
    return None


def _git_log_since(ref: str | None) -> list[str]:
    cmd = ["git", "log", "--oneline", f"{ref}..HEAD"] if ref else ["git", "log", "--oneline"]
    out = _run(cmd)
    return [line for line in out.splitlines() if line.strip()]


def _git_files_since(ref: str | None) -> list[str]:
    if ref:
        cmd = ["git", "diff", "--name-only", f"{ref}..HEAD"]
    else:
        cmd = ["git", "diff", "--name-only", "HEAD~1..HEAD"]
    out = _run(cmd)
    return [line for line in out.splitlines() if line.strip()]


def _bucket_for_path(path: str) -> str:
    if path.startswith("src/frontend/"):
        return "frontend"
    if path.startswith("src/agentic_fleet/"):
        return "backend"
    if path.startswith("docs/") or path.endswith(".md"):
        return "docs"
    if path.startswith("tests/"):
        return "tests"
    if path.startswith(".github/"):
        return "ci"
    if path.startswith("infrastructure/") or path.startswith("docker/"):
        return "infra"
    if path.startswith("scripts/"):
        return "scripts"
    return "other"


def _group_files(files: list[str]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {
        "backend": [],
        "frontend": [],
        "docs": [],
        "tests": [],
        "ci": [],
        "infra": [],
        "scripts": [],
        "other": [],
    }
    for path in files:
        buckets[_bucket_for_path(path)].append(path)
    return buckets


def _emit_text(payload: dict) -> None:
    print("Changelog inputs")
    print(f"- version: {payload.get('version') or 'unknown'}")
    print(f"- date: {payload['date']}")
    print(f"- latest_tag: {payload.get('latest_tag') or 'none'}")
    print(f"- commits: {len(payload['commits'])}")
    print()

    print("Commits:")
    for line in payload["commits"]:
        print(f"- {line}")
    print()

    print("Files by area:")
    for area, items in payload["files_by_area"].items():
        if not items:
            continue
        print(f"- {area} ({len(items)})")
        for path in items:
            print(f"  - {path}")


def main() -> int:
    """Collect changelog inputs from git history and print them."""
    parser = argparse.ArgumentParser(description="Collect changelog inputs from git history.")
    parser.add_argument("--since", help="Git ref to diff from (overrides latest tag)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    root = _repo_root()
    os.chdir(root)

    latest_tag = args.since or _latest_tag()
    commits = _git_log_since(latest_tag)
    files = _git_files_since(latest_tag)
    version = _read_version(root / "pyproject.toml")

    payload = {
        "date": dt.date.today().isoformat(),
        "version": version,
        "latest_tag": latest_tag,
        "commits": commits,
        "files_by_area": _group_files(files),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    _emit_text(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
