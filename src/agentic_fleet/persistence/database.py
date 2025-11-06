"""Database connection manager for aiosqlite."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from .schema import init_database


class DatabaseManager:
    """Manages SQLite database connections with pooling."""

    def __init__(self, db_path: str | Path, init_schema: bool = True) -> None:
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
            init_schema: Whether to initialize schema on first connection
        """
        self.db_path = Path(db_path)
        self._init_schema = init_schema
        self._initialized = False
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Get a database connection with automatic initialization.

        Yields:
            Database connection
        """
        # Initialize schema on first connection
        if not self._initialized:
            async with self._lock:
                if not self._initialized:
                    if self._init_schema:
                        await init_database(self.db_path)
                    self._initialized = True

        async with aiosqlite.connect(str(self.db_path)) as db:
            # Enable foreign keys and row factory
            await db.execute("PRAGMA foreign_keys = ON")
            db.row_factory = aiosqlite.Row
            yield db


# Global database manager instance
_database_manager: DatabaseManager | None = None


def get_database_manager(
    db_path: str | Path | None = None,
    init_schema: bool = True,
) -> DatabaseManager:
    """Get or create database manager instance.

    Args:
        db_path: Path to SQLite database file (required on first call)
        init_schema: Whether to initialize schema on first connection

    Returns:
        Database manager instance

    Raises:
        ValueError: If db_path not provided on first call
    """
    global _database_manager

    if _database_manager is None:
        if db_path is None:
            raise ValueError("db_path required on first call to get_database_manager")
        _database_manager = DatabaseManager(db_path, init_schema)

    return _database_manager


def reset_database_manager() -> None:
    """Reset global database manager (primarily for testing)."""
    global _database_manager
    _database_manager = None
