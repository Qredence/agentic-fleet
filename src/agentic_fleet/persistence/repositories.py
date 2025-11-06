"""Repository classes for database operations."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiosqlite


class ConversationRepository:
    """Repository for conversation operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        """Initialize repository.

        Args:
            db: Database connection
        """
        self.db = db

    async def create(
        self,
        conversation_id: str,
        workflow_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create a new conversation.

        Args:
            conversation_id: Unique conversation ID
            workflow_id: Workflow ID
            metadata: Optional metadata dictionary
        """
        now = time.time()
        await self.db.execute(
            """
            INSERT INTO conversations (id, workflow_id, next_sequence, created_at, updated_at, metadata_json)
            VALUES (?, ?, 0, ?, ?, ?)
            """,
            (
                conversation_id,
                workflow_id,
                now,
                now,
                json.dumps(metadata) if metadata else None,
            ),
        )
        await self.db.commit()

    async def get_next_sequence(self, conversation_id: str) -> int:
        """Get and increment next sequence number atomically.

        Args:
            conversation_id: Conversation ID

        Returns:
            Next sequence number
        """
        async with self.db.execute(
            """
            UPDATE conversations
            SET next_sequence = next_sequence + 1, updated_at = ?
            WHERE id = ?
            RETURNING next_sequence
            """,
            (time.time(), conversation_id),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise ValueError(f"Conversation {conversation_id} not found")
            await self.db.commit()
            return int(row[0]) - 1  # Return pre-increment value

    async def get(self, conversation_id: str) -> dict[str, Any] | None:
        """Get conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation dictionary or None if not found
        """
        async with self.db.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return dict(row)

    async def list_all(self) -> list[dict[str, Any]]:
        """List all conversations ordered by most recent first.

        Returns:
            List of conversation dictionaries
        """
        async with self.db.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_metadata(self, conversation_id: str, metadata: dict[str, Any]) -> None:
        """Update conversation metadata.

        Args:
            conversation_id: Conversation ID
            metadata: Updated metadata dictionary
        """
        await self.db.execute(
            "UPDATE conversations SET metadata_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(metadata), time.time(), conversation_id),
        )
        await self.db.commit()


class MessageRepository:
    """Repository for message operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        """Initialize repository.

        Args:
            db: Database connection
        """
        self.db = db

    async def add(
        self,
        message_id: str,
        conversation_id: str,
        sequence: int,
        role: str,
        content: str,
        reasoning: str | None = None,
        agent_id: str | None = None,
    ) -> None:
        """Add a message.

        Args:
            message_id: Unique message ID
            conversation_id: Conversation ID
            sequence: Sequence number
            role: Message role (user/assistant/system)
            content: Message content
            reasoning: Optional reasoning trace
            agent_id: Optional agent ID
        """
        await self.db.execute(
            """
            INSERT INTO messages
            (id, conversation_id, sequence, role, content, reasoning, agent_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                conversation_id,
                sequence,
                role,
                content,
                reasoning,
                agent_id,
                time.time(),
            ),
        )
        await self.db.commit()

    async def get_history(
        self, conversation_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get message history for conversation.

        Args:
            conversation_id: Conversation ID
            limit: Optional limit on number of messages

        Returns:
            List of message dictionaries ordered by sequence
        """
        query = """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY sequence ASC
        """
        params: tuple[str | int, ...] = (conversation_id,)

        if limit:
            query += " LIMIT ?"
            params = (*params, limit)

        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def count(self, conversation_id: str) -> int:
        """Count messages in conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Message count
        """
        async with self.db.execute(
            "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def delete_range(
        self, conversation_id: str, start_sequence: int, end_sequence: int
    ) -> None:
        """Delete messages in sequence range.

        Args:
            conversation_id: Conversation ID
            start_sequence: Start sequence (inclusive)
            end_sequence: End sequence (inclusive)
        """
        await self.db.execute(
            """
            DELETE FROM messages
            WHERE conversation_id = ? AND sequence >= ? AND sequence <= ?
            """,
            (conversation_id, start_sequence, end_sequence),
        )
        await self.db.commit()


class EventRepository:
    """Repository for event operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        """Initialize repository.

        Args:
            db: Database connection
        """
        self.db = db

    async def add(
        self,
        conversation_id: str,
        sequence: int,
        event_type: str,
        event_data: dict[str, Any],
    ) -> None:
        """Add an event.

        Args:
            conversation_id: Conversation ID
            sequence: Sequence number
            event_type: Event type
            event_data: Event data dictionary
        """
        await self.db.execute(
            """
            INSERT INTO events (conversation_id, sequence, event_type, event_data_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, sequence, event_type, json.dumps(event_data), time.time()),
        )
        await self.db.commit()

    async def get_history(
        self,
        conversation_id: str,
        from_sequence: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get event history for conversation.

        Args:
            conversation_id: Conversation ID
            from_sequence: Optional starting sequence for replay

        Returns:
            List of event dictionaries ordered by sequence
        """
        params: tuple[str | int, ...]
        if from_sequence is not None:
            query = """
                SELECT * FROM events
                WHERE conversation_id = ? AND sequence >= ?
                ORDER BY sequence ASC
            """
            params = (conversation_id, from_sequence)
        else:
            query = """
                SELECT * FROM events
                WHERE conversation_id = ?
                ORDER BY sequence ASC
            """
            params = (conversation_id,)

        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


class LedgerRepository:
    """Repository for ledger snapshot operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        """Initialize repository.

        Args:
            db: Database connection
        """
        self.db = db

    async def add_snapshot(
        self,
        conversation_id: str,
        sequence: int,
        task_id: str,
        goal: str,
        status: str,
        snapshot_data: dict[str, Any],
        agent_id: str | None = None,
    ) -> None:
        """Add a ledger snapshot.

        Args:
            conversation_id: Conversation ID
            sequence: Sequence number
            task_id: Task ID
            goal: Task goal
            status: Task status (pending/in_progress/completed/failed)
            snapshot_data: Full ledger snapshot
            agent_id: Optional agent ID
        """
        await self.db.execute(
            """
            INSERT INTO ledger_snapshots
            (conversation_id, sequence, task_id, goal, status, agent_id, snapshot_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                sequence,
                task_id,
                goal,
                status,
                agent_id,
                json.dumps(snapshot_data),
                time.time(),
            ),
        )
        await self.db.commit()

    async def get_latest(self, conversation_id: str) -> list[dict[str, Any]]:
        """Get latest ledger state for conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of latest ledger items
        """
        # Get latest snapshot for each task_id
        async with self.db.execute(
            """
            SELECT l.* FROM ledger_snapshots l
            INNER JOIN (
                SELECT task_id, MAX(sequence) as max_seq
                FROM ledger_snapshots
                WHERE conversation_id = ?
                GROUP BY task_id
            ) latest ON l.task_id = latest.task_id AND l.sequence = latest.max_seq
            WHERE l.conversation_id = ?
            ORDER BY l.sequence ASC
            """,
            (conversation_id, conversation_id),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


class ReasoningRepository:
    """Repository for reasoning trace operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        """Initialize repository.

        Args:
            db: Database connection
        """
        self.db = db

    async def add(
        self,
        conversation_id: str,
        message_id: str,
        reasoning_text: str,
        effort: str | None = None,
        verbosity: str | None = None,
        model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a reasoning trace.

        Args:
            conversation_id: Conversation ID
            message_id: Message ID
            reasoning_text: Reasoning text
            effort: Reasoning effort level
            verbosity: Reasoning verbosity level
            model: Model ID
            metadata: Optional metadata
        """
        await self.db.execute(
            """
            INSERT INTO reasoning_traces
            (conversation_id, message_id, reasoning_text, effort, verbosity, model, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                message_id,
                reasoning_text,
                effort,
                verbosity,
                model,
                json.dumps(metadata) if metadata else None,
                time.time(),
            ),
        )
        await self.db.commit()

    async def get_by_message(self, message_id: str) -> dict[str, Any] | None:
        """Get reasoning trace for message.

        Args:
            message_id: Message ID

        Returns:
            Reasoning trace dictionary or None
        """
        async with self.db.execute(
            "SELECT * FROM reasoning_traces WHERE message_id = ? LIMIT 1",
            (message_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_by_conversation(self, conversation_id: str) -> list[dict[str, Any]]:
        """Get all reasoning traces for conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of reasoning trace dictionaries
        """
        async with self.db.execute(
            "SELECT * FROM reasoning_traces WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
