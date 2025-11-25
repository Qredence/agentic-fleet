import asyncio

from agentic_fleet.api.db.base_class import Base
from agentic_fleet.api.db.session import engine


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(create_tables())
