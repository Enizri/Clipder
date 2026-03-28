import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = None
async_session_maker = None


def init_database() -> bool:
    global engine, async_session_maker

    settings = get_settings()
    database_url = settings.database_url
    if not database_url:
        logger.error("DATABASE_URL not set in environment")
        return False

    try:
        logger.info("Creating async engine...")
        connect_args = {}
        if "pooler" in database_url:
            connect_args = {
                "ssl": "require",
                "statement_cache_size": 0,
            }

        engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("Database engine created successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def shutdown_database() -> None:
    """Dispose DB engine and reset session maker."""
    global engine, async_session_maker

    async_session_maker = None
    if engine is not None:
        try:
            await engine.dispose()
        finally:
            engine = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if async_session_maker is None:
        if not init_database():
            raise RuntimeError("Database not initialized")
    async with async_session_maker() as session:
        yield session


async def create_tables() -> None:
    if engine is None:
        if not init_database():
            return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
