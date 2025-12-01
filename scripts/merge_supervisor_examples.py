#!/usr/bin/env python3
"""Utility to merge supervisor training examples into the canonical dataset."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT_DATA = REPO_ROOT / "data" / "supervisor_examples.json"
DEFAULT_MODULE_DATA = REPO_ROOT / "src" / "agentic_fleet" / "data" / "supervisor_examples.json"


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, list):  # pragma: no cover - defensive
        raise ValueError(f"Expected list in {path}, found {type(data)!r}")
    return [record for record in data if isinstance(record, dict)]


def merge_records(records: Iterable[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    for bucket in records:
        for record in bucket:
            key = (
                record.get("task", "").strip().lower(),
                record.get("assigned_to", "").strip().lower(),
                record.get("mode", record.get("execution_mode", "")).strip().lower(),
                record.get("team", record.get("team_capabilities", "")).strip().lower(),
                record.get("available_tools", "").strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(record)

    return unique


def write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")


def format_path_for_display(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root-data",
        type=Path,
        default=DEFAULT_ROOT_DATA,
        help="Path to the legacy root-level supervisor_examples.json (if present)",
    )
    parser.add_argument(
        "--module-data",
        type=Path,
        default=DEFAULT_MODULE_DATA,
        help="Path to the canonical supervisor_examples.json inside src/agentic_fleet/data",
    )
    parser.add_argument(
        "--extra",
        type=Path,
        action="append",
        default=[],
        metavar="PATH",
        help="Additional JSON files containing supervisor examples",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_MODULE_DATA,
        help="Where to write the merged dataset",
    )
    parser.add_argument(
        "--mirror-root",
        action="store_true",
        help="Also overwrite the root-level dataset with the merged output",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    buckets: list[list[dict[str, Any]]] = []
    for path in [args.module_data, args.root_data, *args.extra]:
        records = load_records(path)
        display_path = format_path_for_display(path)
        if records:
            print(f"Loaded {len(records):>4} examples from {display_path}")
        else:
            print(f"No examples found at {display_path} (skipping)")
        buckets.append(records)

    merged = merge_records(buckets)
    if not merged:
        raise SystemExit("No supervisor examples were found to merge.")

    write_records(args.output, merged)
    print(f"Wrote {len(merged)} merged examples to {args.output.relative_to(REPO_ROOT)!s}")

    if args.mirror_root and args.root_data:
        write_records(args.root_data, merged)
        print(f"Mirrored merged dataset to {args.root_data.relative_to(REPO_ROOT)!s}")


if __name__ == "__main__":
    main()
