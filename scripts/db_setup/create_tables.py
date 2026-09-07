import asyncio
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine
from backend.models import Base
import os


async def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set")
        return

    print(f"Connecting to: {database_url[:40]}...")

    # Match backend/core/database.py: Supabase pooler needs ssl + no statement cache.
    connect_args = {}
    if "pooler" in database_url:
        connect_args = {
            "ssl": "require",
            "statement_cache_size": 0,
        }

    engine = create_async_engine(database_url, echo=True, connect_args=connect_args)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Tables created successfully!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
