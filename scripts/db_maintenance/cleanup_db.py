"""
Drop all application tables (dev / staging / Supabase only when intentional).

Run from repository root so imports resolve:

    uv run python scripts/db_maintenance/cleanup_db.py
    uv run alembic upgrade head

Uses centralized Settings (same DATABASE_URL / Supabase pooler URL as the app).
The initial Alembic revision must create the full schema on an empty database;
after cleanup, always run ``alembic upgrade head`` before starting the API.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Repo root on sys.path when executed as a file
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.core.config import get_settings  # noqa: E402


def _connect_args(database_url: str) -> dict:
    # Match backend.core.database.init_database pooler handling
    if "pooler" in database_url:
        return {"ssl": "require", "statement_cache_size": 0}
    return {}


# FK-safe order: children before parents. Includes legacy names from older schemas.
_DROP_STATEMENTS: tuple[str, ...] = (
    "DROP TABLE IF EXISTS votes CASCADE",
    "DROP TABLE IF EXISTS vote CASCADE",
    "DROP TABLE IF EXISTS user_clip_history CASCADE",
    "DROP TABLE IF EXISTS user_streamers CASCADE",
    "DROP TABLE IF EXISTS user_streamer CASCADE",
    "DROP TABLE IF EXISTS clip_video_cache CASCADE",
    "DROP TABLE IF EXISTS leaderboard_snapshots CASCADE",
    "DROP TABLE IF EXISTS leaderboard_monthly_summary CASCADE",
    "DROP TABLE IF EXISTS clips CASCADE",
    "DROP TABLE IF EXISTS clip CASCADE",
    "DROP TABLE IF EXISTS users CASCADE",
    "DROP TABLE IF EXISTS \"user\" CASCADE",
    "DROP TABLE IF EXISTS alembic_version CASCADE",
)


async def cleanup() -> None:
    settings = get_settings()
    database_url = settings.database_url
    if not database_url:
        print("ERROR: DATABASE_URL missing in Settings / .env")
        return

    preview = database_url[:60] + ("..." if len(database_url) > 60 else "")
    print(f"Connecting to: {preview}")

    engine = create_async_engine(
        database_url,
        echo=False,
        connect_args=_connect_args(database_url),
    )
    try:
        async with engine.begin() as conn:
            for stmt in _DROP_STATEMENTS:
                name = stmt.split("IF EXISTS ")[1].split(" CASCADE")[0]
                print(f"Dropping {name}...")
                await conn.execute(text(stmt))
        print("Database cleaned successfully. Run: uv run alembic upgrade head")
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup())
