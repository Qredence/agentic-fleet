"""SQLite database schema for conversation persistence.

Defines tables for:
- conversations: Main conversation records with workflow metadata
- messages: User/assistant messages with sequence ordering
- events: SSE events with sequence ordering
- ledger_snapshots: Task ledger state at specific sequences
- reasoning_traces: Structured reasoning metadata linked to messages
"""

from pathlib import Path

import aiosqlite

# SQL schema definitions
SCHEMA_VERSION = 1

CONVERSATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    next_sequence INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    metadata_json TEXT
);
"""

MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    reasoning TEXT,
    agent_id TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_sequence
ON messages(conversation_id, sequence);
"""

EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_data_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_events_conversation_sequence
ON events(conversation_id, sequence);
"""

LEDGER_SNAPSHOTS_TABLE = """
CREATE TABLE IF NOT EXISTS ledger_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    task_id TEXT NOT NULL,
    goal TEXT NOT NULL,
    status TEXT NOT NULL,
    agent_id TEXT,
    snapshot_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_ledger_conversation_sequence
ON ledger_snapshots(conversation_id, sequence);
"""

REASONING_TRACES_TABLE = """
CREATE TABLE IF NOT EXISTS reasoning_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    reasoning_text TEXT NOT NULL,
    effort TEXT,
    verbosity TEXT,
    model TEXT,
    metadata_json TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_reasoning_conversation
ON reasoning_traces(conversation_id);
CREATE INDEX IF NOT EXISTS idx_reasoning_message
ON reasoning_traces(message_id);
"""

SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL
);
"""


async def init_database(db_path: str | Path) -> None:
    """Initialize database schema.

    Args:
        db_path: Path to SQLite database file
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(db_path)) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")

        # Create tables using executescript to handle multiple statements
        await db.executescript(
            CONVERSATIONS_TABLE
            + ";\n"
            + MESSAGES_TABLE
            + ";\n"
            + EVENTS_TABLE
            + ";\n"
            + LEDGER_SNAPSHOTS_TABLE
            + ";\n"
            + REASONING_TRACES_TABLE
            + ";\n"
            + SCHEMA_VERSION_TABLE
        )

        # Record schema version
        await db.execute(
            "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, ?)",
            (SCHEMA_VERSION, __import__("time").time()),
        )

        await db.commit()


async def get_schema_version(db_path: str | Path) -> int | None:
    """Get current schema version.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Current schema version or None if not initialized
    """
    try:
        async with (
            aiosqlite.connect(str(db_path)) as db,
            db.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            ) as cursor,
        ):
            row = await cursor.fetchone()
            return row[0] if row else None
    except Exception:
        return None
