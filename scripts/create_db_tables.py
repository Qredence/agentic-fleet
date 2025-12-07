"""DEPRECATED: This script references modules that have been removed.

The db module (agentic_fleet.api.db) no longer exists in the current codebase.
This script is kept for reference but will not function.
Consider using the cosmos.py utilities or removing this script entirely.
"""

import asyncio

from agentic_fleet.api.db.base_class import Base  # type: ignore[import]
from agentic_fleet.api.db.session import engine  # type: ignore[import]


async def create_tables():
    """
    Create database tables defined on Base.metadata in the database bound to `engine`.

    Any tables described by the SQLAlchemy declarative metadata that are missing from the target database will be created.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(create_tables())
