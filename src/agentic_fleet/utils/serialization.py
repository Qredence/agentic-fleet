"""Serialization utilities for JSON and JSONL loading.

This module provides centralized utilities for loading JSON and JSONL files
with consistent error handling and validation.
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from agentic_fleet.utils.infra.logging import setup_logger

logger = setup_logger(__name__)


def load_json(file_path: Path, default: Any = None, validate_list: bool = False) -> Any:
    """Load JSON from a file with error handling.

    Args:
        file_path: Path to JSON file
        default: Default value to return if file doesn't exist or parsing fails
        validate_list: If True, ensure result is a list and filter to dict items

    Returns:
        Parsed JSON data, or default if loading fails
    """
    if not file_path.exists():
        if default is not None:
            return default
        return [] if validate_list else {}

    try:
        data = json.loads(file_path.read_text())
        if validate_list:
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            logger.warning(f"Expected list in {file_path}, got {type(data)}")
            return []
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from {file_path}: {e}")
        return default if default is not None else ([] if validate_list else {})
    except Exception as e:
        logger.error(f"Failed to load JSON from {file_path}: {e}")
        return default if default is not None else ([] if validate_list else {})


def _parse_jsonl_line(line: str, line_num: int, file_path: Path) -> dict[str, Any] | None:
    try:
        parsed = json.loads(line)
        if isinstance(parsed, dict):
            return parsed
        logger.warning(f"Line {line_num} in {file_path} is not a dict, skipping")
    except json.JSONDecodeError as e:
        logger.warning(
            f"Failed to parse JSONL line {line_num} in {file_path}: {e}. Line preview: {line[:100]}"
        )
    return None


def load_jsonl(
    file_path: Path, limit: int | None = None, default: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Load JSONL (JSON Lines) from a file with error handling.

    Args:
        file_path: Path to JSONL file
        limit: Optional limit on number of entries to return (returns last N)
        default: Default value to return if file doesn't exist

    Returns:
        List of parsed JSON objects from each line
    """
    if not file_path.exists():
        return default if default is not None else []

    if limit is not None and limit < 0:
        logger.warning(f"Negative limit {limit} provided for {file_path}, returning default")
        return default if default is not None else []

    executions: deque[dict[str, Any]] | list[dict[str, Any]]
    executions = deque(maxlen=limit) if limit is not None else []
    try:
        with file_path.open(encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                parsed = _parse_jsonl_line(line, line_num, file_path)
                if parsed is not None:
                    executions.append(parsed)
    except Exception as e:
        logger.error(f"Failed to read JSONL file {file_path}: {e}")
        return default if default is not None else []

    return list(executions)


def save_json(file_path: Path, data: Any, indent: int = 2) -> None:
    """Save data to JSON file with error handling.

    Args:
        file_path: Path to save JSON file
        data: Data to serialize
        indent: JSON indentation level
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=indent))
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        raise


def save_jsonl(file_path: Path, items: list[dict[str, Any]], append: bool = False) -> None:
    """Save list of dicts to JSONL file.

    Args:
        file_path: Path to save JSONL file
        items: List of dictionaries to write
        append: If True, append to existing file; otherwise overwrite
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append and file_path.exists() else "w"
        with file_path.open(mode) as f:
            for item in items:
                f.write(json.dumps(item) + "\n")
    except Exception as e:
        logger.error(f"Failed to save JSONL to {file_path}: {e}")
        raise
