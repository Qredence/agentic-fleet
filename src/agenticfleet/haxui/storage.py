"""SQLite-backed persistence helpers for HaxUI state."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .models import (
    ConversationItem,
    ConversationItemsResponse,
    ConversationListResponse,
    ConversationSummary,
)

DEFAULT_DB_PATH = Path("var") / "haxui" / "state.db"


class SQLiteConversationStore:
    """Conversation store compatible with the in-memory variant but backed by SQLite."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path or DEFAULT_DB_PATH).resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_done = asyncio.Event()

    async def initialise(self) -> None:
        """Ensure tables exist before first use."""
        if self._init_done.is_set():
            return
        await asyncio.to_thread(self._create_tables)
        self._init_done.set()

    def _connect(self) -> sqlite3.Connection:
        # Always create a new connection per operation; never share connections between threads.
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    created_at INTEGER NOT NULL,
                    metadata TEXT
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );
                """
            )
            conn.commit()

    async def create(self, summary: ConversationSummary) -> None:
        await self.initialise()
        metadata_json = json.dumps(summary.metadata or {})
        await asyncio.to_thread(
            self._insert_conversation, summary.id, summary.created_at, metadata_json
        )

    def _insert_conversation(self, conv_id: str, created_at: int, metadata_json: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO conversations (id, created_at, metadata)
                VALUES (?, ?, ?)
                """,
                (conv_id, created_at, metadata_json),
            )
            conn.commit()

    async def delete(self, conversation_id: str) -> None:
        await self.initialise()
        await asyncio.to_thread(self._delete_conversation, conversation_id)

    def _delete_conversation(self, conversation_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()

    async def upsert_message(
        self,
        *,
        message: ConversationItem,
        conversation_id: str,
    ) -> None:
        await self.initialise()
        await asyncio.to_thread(
            self._insert_message,
            message.id,
            conversation_id,
            message.role,
            json.dumps(message.content),
            message.status,
            message.created_at,
        )

    def _insert_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content_json: str,
        status: str,
        created_at: int,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO messages
                (id, conversation_id, role, content, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (message_id, conversation_id, role, content_json, status, created_at),
            )
            conn.commit()

    async def list_conversations(self) -> ConversationListResponse:
        await self.initialise()
        rows = await asyncio.to_thread(self._fetch_conversations)
        summaries = [
            ConversationSummary(
                id=row["id"],
                created_at=row["created_at"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else None,
            )
            for row in rows
        ]
        return ConversationListResponse(data=summaries)

    def _fetch_conversations(self) -> Iterable[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id, created_at, metadata FROM conversations ORDER BY created_at DESC"
            )
            return cursor.fetchall()

    async def fetch_conversation(self, conversation_id: str) -> ConversationSummary | None:
        await self.initialise()
        row = await asyncio.to_thread(self._fetch_conversation_row, conversation_id)
        if row is None:
            return None
        metadata = json.loads(row["metadata"]) if row["metadata"] else None
        return ConversationSummary(id=row["id"], created_at=row["created_at"], metadata=metadata)

    def _fetch_conversation_row(self, conversation_id: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id, created_at, metadata FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            result = cursor.fetchone()
            return result  # type: ignore[no-any-return]

    async def list_items(self, conversation_id: str) -> ConversationItemsResponse:
        await self.initialise()
        rows = await asyncio.to_thread(self._fetch_messages, conversation_id)
        items = [
            ConversationItem(
                id=row["id"],
                role=row["role"],
                content=json.loads(row["content"]),
                status=row["status"],
                created_at=row["created_at"],
                type="message",
            )
            for row in rows
        ]
        return ConversationItemsResponse(data=items)

    def _fetch_messages(self, conversation_id: str) -> Iterable[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT id, role, content, status, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            )
            return cursor.fetchall()


class SQLiteApprovalStore:
    """Persistence for pending HITL approvals to expose to the frontend."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path or DEFAULT_DB_PATH).resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_done = asyncio.Event()

    async def initialise(self) -> None:
        if self._init_done.is_set():
            return
        await asyncio.to_thread(self._create_table)
        self._init_done.set()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    request_id TEXT PRIMARY KEY,
                    operation_type TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    details TEXT,
                    code TEXT,
                    status TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    reason TEXT
                )"""
            )
            try:
                conn.execute("ALTER TABLE approvals ADD COLUMN reason TEXT")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" in str(exc):
                    # Column already exists
                    pass
                else:
                    import logging

                    logging.warning(f"Failed to migrate approvals table: {exc}")
                    raise
            conn.commit()
            conn.commit()

    async def add_request(self, request: dict[str, Any]) -> None:
        await self.initialise()
        await asyncio.to_thread(self._insert_request, request)

    def _insert_request(self, request: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO approvals (
                    request_id,
                    operation_type,
                    agent_name,
                    operation,
                    details,
                    code,
                    status,
                    created_at,
                    timestamp,
                    reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request["request_id"],
                    request["operation_type"],
                    request["agent_name"],
                    request["operation"],
                    json.dumps(request.get("details") or {}),
                    request.get("code"),
                    request.get("status", "pending"),
                    int(time.time()),
                    request["timestamp"],
                    request.get("reason"),
                ),
            )
            conn.commit()

    async def mark_completed(
        self,
        request_id: str,
        status: str,
        *,
        reason: str | None = None,
    ) -> bool:
        await self.initialise()
        return await asyncio.to_thread(self._update_status, request_id, status, reason)

    def _update_status(self, request_id: str, status: str, reason: str | None) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE approvals SET status = ?, reason = ? WHERE request_id = ?",
                (status, reason, request_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    async def remove(self, request_id: str) -> None:
        await self.initialise()
        await asyncio.to_thread(self._delete_request, request_id)

    def _delete_request(self, request_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM approvals WHERE request_id = ?", (request_id,))
            conn.commit()

    async def list_pending(self) -> list[dict[str, Any]]:
        await self.initialise()
        rows = await asyncio.to_thread(self._fetch_pending)
        pending: list[dict[str, Any]] = []
        for row in rows:
            pending.append(
                {
                    "request_id": row["request_id"],
                    "operation_type": row["operation_type"],
                    "agent_name": row["agent_name"],
                    "operation": row["operation"],
                    "details": json.loads(row["details"]) if row["details"] else {},
                    "code": row["code"],
                    "timestamp": row["timestamp"],
                    "status": row["status"],
                    "reason": row["reason"],
                }
            )
        return pending

    def _fetch_pending(self) -> Iterable[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT
                    request_id,
                    operation_type,
                    agent_name,
                    operation,
                    details,
                    code,
                    timestamp,
                    status,
                    reason
                FROM approvals
                WHERE status = 'pending'
                ORDER BY created_at ASC
                """
            )
            return cursor.fetchall()
