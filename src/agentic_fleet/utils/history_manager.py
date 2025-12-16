"""
History management utilities for execution history.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Any

import aiofiles

from ..utils.models import RoutingDecision
from ..workflows.exceptions import HistoryError
from .cfg import DEFAULT_HISTORY_PATH

logger = logging.getLogger(__name__)

# Track background tasks to satisfy Ruff RUF006 and prevent premature GC of tasks.
# Tasks are added when created and automatically removed on completion.
_background_tasks: set[asyncio.Task[Any]] = set()


class FleetJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for fleet objects."""

    def default(self, o: Any) -> Any:
        """Override default serialization for custom types."""
        if isinstance(o, RoutingDecision):
            return o.to_dict()
        if hasattr(o, "to_dict"):
            return o.to_dict()
        return super().default(o)


class HistoryManager:
    """Manages execution history storage and retrieval."""

    def __init__(
        self, history_format: str = "jsonl", max_entries: int | None = None, index_size: int = 1000
    ):
        """
        Initialize history manager.

        Args:
            history_format: Format to use ("jsonl" or "json")
            max_entries: Maximum number of entries to keep (None for unlimited)
            index_size: Maximum number of recent executions to keep in memory index
        """
        self.history_format = history_format
        self.max_entries = max_entries
        self.history_dir = Path(DEFAULT_HISTORY_PATH).parent
        self.history_dir.mkdir(parents=True, exist_ok=True)

        # In-memory index for fast O(1) lookups of recent executions
        # Using OrderedDict for true O(1) LRU operations (move_to_end is O(1))
        self._recent_executions_index: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._index_size_limit = index_size

        # Warn about JSON format performance implications
        if history_format == "json":
            logger.warning(
                "JSON history format selected. This format requires full file read/write "
                "on each save, which can be slow for large histories. Consider using "
                "'jsonl' format for better performance (O(1) append vs O(n) rewrite)."
            )

    def _update_index(self, execution: dict[str, Any]) -> None:
        """Update in-memory index with new execution for O(1) lookups.

        Uses OrderedDict for true O(1) LRU operations. The move_to_end() method
        is O(1) unlike list.remove() which would be O(n).

        Args:
            execution: Execution data dictionary
        """
        workflow_id = execution.get("workflowId")
        if not workflow_id:
            return

        # Add/update entry and move to end (most recently used)
        # OrderedDict.__setitem__ + move_to_end maintains insertion order properly
        self._recent_executions_index[workflow_id] = execution
        self._recent_executions_index.move_to_end(workflow_id)

        # Trim index if it exceeds size limit (evict oldest/least recently used)
        while len(self._recent_executions_index) > self._index_size_limit:
            # Pop first item (oldest/least recently used) - O(1) operation
            oldest_id, _ = self._recent_executions_index.popitem(last=False)
            logger.debug(f"Evicted execution {oldest_id} from index (LRU)")

    async def save_execution_async(self, execution: dict[str, Any]) -> str:
        """
        Save execution to history file asynchronously.

        Args:
            execution: Execution data dictionary

        Returns:
            Path to the history file that was written

        Raises:
            HistoryError: If saving fails
        """
        # Update in-memory index for fast lookups
        self._update_index(execution)

        try:
            if self.history_format == "jsonl":
                history_file = await self._save_jsonl_async(execution)
            else:
                history_file = await self._save_json_async(execution)
        except Exception as e:
            history_file = (
                str(self.history_dir / f"execution_history.{self.history_format}")
                if self.history_format == "jsonl"
                else str(self.history_dir / "execution_history.json")
            )
            raise HistoryError(f"Failed to save execution history: {e}", history_file) from e

        # Best-effort mirror to Cosmos DB without affecting main execution.
        async def mirror_in_background():
            try:
                from .cosmos import mirror_execution_history

                await asyncio.to_thread(mirror_execution_history, execution)
            except Exception:  # pragma: no cover - defensive guardrail
                logger.debug("Cosmos history mirror failed (async path)", exc_info=True)

        # Create background mirror task and retain reference until completion (RUF006)
        task = asyncio.create_task(mirror_in_background())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        return history_file

    def save_execution(self, execution: dict[str, Any]) -> str:
        """
        Save execution to history file (synchronous wrapper).

        Args:
            execution: Execution data dictionary

        Returns:
            Path to the history file that was written

        Raises:
            HistoryError: If saving fails
        """
        # Update in-memory index for fast lookups
        self._update_index(execution)

        # For backward compatibility, use the original synchronous implementation
        try:
            if self.history_format == "jsonl":
                history_file = self._save_jsonl(execution)
            else:
                history_file = self._save_json(execution)
        except Exception as e:
            history_file = (
                str(self.history_dir / f"execution_history.{self.history_format}")
                if self.history_format == "jsonl"
                else str(self.history_dir / "execution_history.json")
            )
            raise HistoryError(f"Failed to save execution history: {e}", history_file) from e

        # Best-effort mirror to Cosmos DB. Errors are caught to avoid affecting main execution success.
        try:
            from .cosmos import mirror_execution_history

            mirror_execution_history(execution)
        except Exception:  # pragma: no cover - defensive guardrail
            logger.debug("Cosmos history mirror failed (sync path)", exc_info=True)

        return history_file

    async def _save_jsonl_async(self, execution: dict[str, Any]) -> str:
        """Save execution in JSONL format (append mode, async)."""
        history_file = self.history_dir / "execution_history.jsonl"

        async with aiofiles.open(history_file, "a") as f:
            content = json.dumps(execution, cls=FleetJSONEncoder) + "\n"
            await f.write(content)

        logger.debug(f"Execution appended to {history_file}")

        # Rotate if needed (use efficient rotation)
        if self.max_entries:
            await self._rotate_jsonl_async_optimized(history_file, self.max_entries)

        return str(history_file)

    def _save_jsonl(self, execution: dict[str, Any]) -> str:
        """Save execution in JSONL format (append mode)."""
        history_file = self.history_dir / "execution_history.jsonl"

        with open(history_file, "a") as f:
            json.dump(execution, f, cls=FleetJSONEncoder)
            f.write("\n")

        logger.debug(f"Execution appended to {history_file}")

        # Rotate if needed
        if self.max_entries:
            self._rotate_jsonl(history_file, self.max_entries)

        return str(history_file)

    async def _save_json_async(self, execution: dict[str, Any]) -> str:
        """Save execution in JSON format (full read/write, async)."""
        history_file = self.history_dir / "execution_history.json"

        # Load existing history if file exists
        existing_history: list[dict[str, Any]] = []
        if history_file.exists():
            try:
                async with aiofiles.open(history_file) as f:
                    content = await f.read()
                    existing_history = json.loads(content)
            except Exception as e:
                logger.warning(f"Failed to load existing history: {e}")
                existing_history = []

        # Append new execution
        existing_history.append(execution)

        # Rotate if needed
        if self.max_entries and len(existing_history) > self.max_entries:
            existing_history = existing_history[-self.max_entries :]

        # Save updated history
        async with aiofiles.open(history_file, "w") as f:
            content = json.dumps(existing_history, indent=2, cls=FleetJSONEncoder)
            await f.write(content)

        logger.debug(f"Execution history saved to {history_file}")
        return str(history_file)

    def _save_json(self, execution: dict[str, Any]) -> str:
        """Save execution in JSON format (full read/write)."""
        history_file = self.history_dir / "execution_history.json"

        # Load existing history if file exists
        existing_history: list[dict[str, Any]] = []
        if history_file.exists():
            try:
                with open(history_file) as f:
                    existing_history = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load existing history: {e}")
                existing_history = []

        # Append new execution
        existing_history.append(execution)

        # Rotate if needed
        if self.max_entries and len(existing_history) > self.max_entries:
            existing_history = existing_history[-self.max_entries :]

        # Save updated history
        with open(history_file, "w") as f:
            json.dump(existing_history, f, indent=2, cls=FleetJSONEncoder)

        logger.debug(f"Execution history saved to {history_file}")
        return str(history_file)

    async def _rotate_jsonl_async_optimized(self, history_file: Path, max_entries: int) -> None:
        """Optimized async rotation - only rotate periodically to avoid frequent I/O."""
        try:
            # Only rotate every 100th write to reduce overhead
            # Check file size as a proxy for number of entries (roughly)
            file_size = history_file.stat().st_size if history_file.exists() else 0
            avg_entry_size = 500  # Rough estimate

            # Only check rotation if file is large enough
            estimated_entries = file_size // avg_entry_size
            if estimated_entries <= max_entries:
                return

            # Use deque for efficient tail extraction
            from collections import deque

            last_lines: deque[str] = deque(maxlen=max_entries)

            # Read and keep only last N lines
            async with aiofiles.open(history_file) as f:
                async for line in f:
                    last_lines.append(line)

            # Write back only the last N lines
            async with aiofiles.open(history_file, "w") as f:
                await f.writelines(last_lines)

            logger.debug(
                "Optimized rotation: kept last %d entries (file reduced from %d)",
                max_entries,
                estimated_entries,
            )

        except Exception as e:
            logger.warning(f"Failed to rotate history file: {e}")

    def _rotate_jsonl(self, history_file: Path, max_entries: int) -> None:
        """Rotate JSONL file to keep only last N entries."""
        try:
            # Check file size to avoid unnecessary work
            if not history_file.exists():
                return

            # Use deque for efficient tail extraction
            from collections import deque

            with open(history_file) as f:
                last_lines = deque(f, maxlen=max_entries)

            # Write back only the last N lines
            with open(history_file, "w") as f:
                f.writelines(last_lines)

            logger.debug(f"Rotated history file to keep last {max_entries} entries")
        except Exception as e:
            logger.warning(f"Failed to rotate history file: {e}")

    def get_execution(self, workflow_id: str) -> dict[str, Any] | None:
        """
        Retrieve a specific execution by ID with O(1) index lookup for recent entries.

        Args:
            workflow_id: The workflow ID to retrieve

        Returns:
            Execution dictionary or None if not found
        """
        # Check in-memory index first for O(1) lookup
        if workflow_id in self._recent_executions_index:
            logger.debug(f"Found execution {workflow_id} in memory index (O(1) lookup)")
            # Update LRU order on access (move to end = most recently used)
            self._recent_executions_index.move_to_end(workflow_id)
            return self._recent_executions_index[workflow_id]

        # Try Cosmos DB first if enabled
        try:
            from .cosmos import get_execution, is_cosmos_enabled

            if is_cosmos_enabled():
                execution = get_execution(workflow_id)
                if execution:
                    # Add to index for future lookups
                    self._update_index(execution)
                    return execution
        except Exception as e:
            logger.warning(f"Failed to load execution from Cosmos DB: {e}")

        # Fallback to file scan for older entries (O(n) operation)
        logger.debug(f"Execution {workflow_id} not in index, scanning files (O(n) lookup)")

        # Scan local files
        # Check JSONL first
        jsonl_file = self.history_dir / "execution_history.jsonl"
        if jsonl_file.exists():
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if entry.get("workflowId") == workflow_id:
                                # Add to index for future lookups
                                self._update_index(entry)
                                return entry
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.warning(f"Failed to scan JSONL history: {e}")

        # Check JSON
        json_file = self.history_dir / "execution_history.json"
        if json_file.exists():
            try:
                with open(json_file) as f:
                    entries = json.load(f)
                    for entry in entries:
                        if entry.get("workflowId") == workflow_id:
                            # Add to index for future lookups
                            self._update_index(entry)
                            return entry
            except Exception as e:
                logger.warning(f"Failed to scan JSON history: {e}")

        return None

    def update_execution(self, workflow_id: str, patch: dict[str, Any]) -> bool:
        """Update a specific execution record in-place (best-effort).

        For JSONL history, this rewrites the file to preserve ordering.
        For JSON history, this rewrites the JSON list.

        Returns:
            True if an execution was updated, False if not found.
        """
        if not workflow_id:
            return False

        # Update in-memory index if present
        if workflow_id in self._recent_executions_index:
            existing = self._recent_executions_index[workflow_id]
            existing.update(patch)
            self._recent_executions_index[workflow_id] = existing
            self._recent_executions_index.move_to_end(workflow_id)

        jsonl_file = self.history_dir / "execution_history.jsonl"
        if jsonl_file.exists():
            try:
                updated = False
                tmp_path = self.history_dir / "execution_history.jsonl.tmp"
                with open(jsonl_file) as src, open(tmp_path, "w") as dst:
                    for line in src:
                        if not line.strip():
                            dst.write(line)
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            dst.write(line)
                            continue
                        if obj.get("workflowId") == workflow_id:
                            obj.update(patch)
                            updated = True
                            dst.write(json.dumps(obj, cls=FleetJSONEncoder) + "\n")
                        else:
                            dst.write(json.dumps(obj, cls=FleetJSONEncoder) + "\n")
                tmp_path.replace(jsonl_file)
                return updated
            except Exception as e:
                logger.warning("Failed to update JSONL history: %s", e)  # nosec B608

        json_file = self.history_dir / "execution_history.json"
        if json_file.exists():
            try:
                with open(json_file) as f:
                    entries = json.load(f)
                updated = False
                for entry in entries if isinstance(entries, list) else []:
                    if entry.get("workflowId") == workflow_id:
                        entry.update(patch)
                        updated = True
                        break
                if updated:
                    with open(json_file, "w") as f:
                        json.dump(entries, f, indent=2, cls=FleetJSONEncoder)
                return updated
            except Exception as e:
                logger.warning("Failed to update JSON history: %s", e)  # nosec B608

        return False

    def delete_execution(self, workflow_id: str) -> bool:
        """
        Delete a specific execution by ID.

        Args:
            workflow_id: The workflow ID to delete

        Returns:
            True if deleted, False otherwise
        """
        deleted = False

        # Handle JSONL
        jsonl_file = self.history_dir / "execution_history.jsonl"
        if jsonl_file.exists():
            try:
                lines = []
                file_changed = False
                with open(jsonl_file) as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if entry.get("workflowId") == workflow_id:
                                file_changed = True
                                deleted = True
                                continue  # Skip this line
                            lines.append(line)
                        except json.JSONDecodeError:
                            lines.append(line)

                if file_changed:
                    with open(jsonl_file, "w") as f:
                        f.writelines(lines)
            except Exception as e:
                logger.warning(f"Failed to delete from JSONL history: {e}")  # nosec B608

        # Handle JSON
        json_file = self.history_dir / "execution_history.json"
        if json_file.exists():
            try:
                with open(json_file) as f:
                    entries = json.load(f)

                new_entries = [e for e in entries if e.get("workflowId") != workflow_id]
                if len(new_entries) < len(entries):
                    deleted = True
                    with open(json_file, "w") as f:
                        json.dump(new_entries, f, indent=2, cls=FleetJSONEncoder)
            except Exception as e:
                logger.warning(f"Failed to delete from JSON history: {e}")  # nosec B608

        return deleted

    def get_recent_executions(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        """
        Get recent executions, newest first.

        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip

        Returns:
            List of execution dictionaries
        """
        # Optimized: Load only needed entries using tail-read
        # We need (offset + limit) entries from the end, then slice
        needed = offset + limit
        executions = self._load_history_tail(needed)

        # Already in newest-first order from _load_history_tail
        return executions[offset : offset + limit]

    def _load_history_tail(self, n: int) -> list[dict[str, Any]]:
        """
        Efficiently load the last N entries from history (newest first).

        Uses deque for O(n) memory instead of loading entire file.

        Args:
            n: Number of entries to load from the end

        Returns:
            List of execution dictionaries, newest first
        """
        from collections import deque

        # Try Cosmos DB first if enabled
        try:
            from .cosmos import get_default_user_id, is_cosmos_enabled, load_execution_history

            if is_cosmos_enabled():
                history = load_execution_history(limit=n, user_id=get_default_user_id())
                if history:
                    # Cosmos returns newest first
                    return history
        except Exception as e:
            logger.warning(f"Failed to load history from Cosmos DB: {e}")

        # Try JSONL (preferred format) with efficient tail read
        jsonl_file = self.history_dir / "execution_history.jsonl"
        if jsonl_file.exists():
            try:
                executions: deque[dict[str, Any]] = deque(maxlen=n)
                with open(jsonl_file) as f:
                    for line in f:
                        if line.strip():
                            try:
                                executions.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
                # Return newest first
                result = list(executions)
                result.reverse()
                return result
            except Exception as e:
                logger.warning(f"Failed to load JSONL history tail: {e}")

        # Fall back to JSON format
        json_file = self.history_dir / "execution_history.json"
        if json_file.exists():
            try:
                with open(json_file) as f:
                    all_executions = json.load(f)
                # Take last N and reverse for newest first
                result = all_executions[-n:] if n else all_executions
                result.reverse()
                return result
            except Exception as e:
                logger.warning(f"Failed to load JSON history tail: {e}")

        return []

    def load_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Load execution history.

        Args:
            limit: Maximum number of entries to return (None for all)

        Returns:
            List of execution dictionaries
        """
        # Try Cosmos DB first if enabled
        try:
            from .cosmos import get_default_user_id, is_cosmos_enabled, load_execution_history

            if is_cosmos_enabled():
                history = load_execution_history(limit=limit or 20, user_id=get_default_user_id())
                if history:
                    return history
        except Exception as e:
            logger.warning(f"Failed to load history from Cosmos DB: {e}")

        # Try JSONL first (preferred format)
        jsonl_file = self.history_dir / "execution_history.jsonl"
        if jsonl_file.exists():
            try:
                return self._load_jsonl(jsonl_file, limit)
            except Exception as e:
                logger.warning(f"Failed to load JSONL history: {e}")

        # Fall back to JSON format
        json_file = self.history_dir / "execution_history.json"
        if json_file.exists():
            try:
                return self._load_json(json_file, limit)
            except Exception as e:
                logger.warning(f"Failed to load JSON history: {e}")

        return []

    def _load_jsonl(self, history_file: Path, limit: int | None = None) -> list[dict[str, Any]]:
        """Load history from JSONL file."""
        executions = []
        with open(history_file) as f:
            for line in f:
                if line.strip():
                    try:
                        executions.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSONL line: {e}")
                        continue

        # Return last N entries if limit specified
        if limit:
            return executions[-limit:]
        return executions

    def _load_json(self, history_file: Path, limit: int | None = None) -> list[dict[str, Any]]:
        """Load history from JSON file."""
        with open(history_file) as f:
            executions = json.load(f)

        # Return last N entries if limit specified
        if limit:
            return executions[-limit:]
        return executions

    def clear_history(self, keep_recent: int = 0):
        """
        Clear execution history.

        Args:
            keep_recent: Number of recent entries to keep (0 to clear all)
        """
        jsonl_file = self.history_dir / "execution_history.jsonl"
        json_file = self.history_dir / "execution_history.json"

        if keep_recent > 0:
            # Keep recent entries
            if jsonl_file.exists():
                self._rotate_jsonl(jsonl_file, keep_recent)
            if json_file.exists():
                executions = self._load_json(json_file, keep_recent)
                with open(json_file, "w") as f:
                    json.dump(executions, f, indent=2)
        else:
            # Clear all
            if jsonl_file.exists():
                jsonl_file.unlink()
            if json_file.exists():
                json_file.unlink()
            logger.info("Execution history cleared")

    def get_history_stats(self) -> dict[str, Any]:
        """
        Get statistics about execution history.

        Returns:
            Dictionary with statistics
        """
        executions = self.load_history()
        if not executions:
            return {"total_executions": 0}

        total_time = sum(
            e.get("total_time_seconds", 0) for e in executions if "total_time_seconds" in e
        )
        quality_entries = [e for e in executions if "quality" in e]
        avg_quality = (
            sum(e.get("quality", {}).get("score", 0) for e in quality_entries)
            / len(quality_entries)
            if quality_entries
            else 0
        )

        return {
            "total_executions": len(executions),
            "total_time_seconds": total_time,
            "average_time_seconds": total_time / len(executions) if executions else 0,
            "average_quality_score": avg_quality,
            "format": self.history_format,
        }
