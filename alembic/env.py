import os
import asyncio
from logging.config import fileConfig

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from backend.core.database import Base

# Import every model so Alembic can detect all tables in metadata
from backend.models import (  # noqa: F401
    User,
    Clip,
    Vote,
    UserStreamer,
    UserClipHistory,
    LeaderboardSnapshot,
    LeaderboardMonthlySummary,
    ClipVideoCache,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Return DATABASE_URL from env; raise clearly if missing."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Set it in your .env file before running migrations."
        )
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection needed)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with an async engine."""
    url = get_url()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    # Supabase pooler requires SSL + disabled statement caching
    connect_args = (
        {"ssl": "require", "statement_cache_size": 0} if "pooler" in url else {}
    )

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migration mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
