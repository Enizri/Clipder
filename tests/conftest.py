"""
Pytest configuration and fixtures for ClipApp integration tests.
"""

import os
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from main import app
from backend.models import Base, User, Clip
from backend.core.database import get_db
from backend.core.config import get_settings


# Use PostgreSQL test database
# Try to use environment variable, but default to local test DB
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/clipder_test",
)


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine"""
    # Use PostgreSQL with asyncpg driver
    engine = create_async_engine(
        TEST_DATABASE_URL, echo=False, connect_args={"timeout": 5, "command_timeout": 5}
    )

    try:
        # Test connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(
            f"PostgreSQL test database not available: {TEST_DATABASE_URL}\n"
            f"Error: {str(e)}\n"
            f"To run tests, set TEST_DATABASE_URL environment variable or "
            f"ensure PostgreSQL is running locally"
        )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception as e:
        print(f"Warning: Failed to drop tables: {e}")

    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine):
    """Create test database session"""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_client(test_db):
    """Create FastAPI test client with mocked database"""

    async def override_get_db():
        return test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_clip(test_db: AsyncSession):
    """Create a test clip"""
    clip = Clip(
        title="Test Clip 1",
        creator="Test Creator",
        url="https://twitch.tv/test/clip/1",
        thumbnail_url="https://example.com/thumb1.jpg",
        view_count=100,
        monthly_likes=50,
        monthly_dislikes=5,
    )
    test_db.add(clip)
    await test_db.commit()
    await test_db.refresh(clip)
    return clip


@pytest_asyncio.fixture
async def test_clips(test_db: AsyncSession):
    """Create 15 test clips with varying likes"""
    clips = []
    for i in range(1, 16):
        clip = Clip(
            title=f"Test Clip {i}",
            creator=f"Creator {chr(65 + (i % 26))}",
            url=f"https://twitch.tv/test/clip/{i}",
            thumbnail_url=f"https://example.com/thumb{i}.jpg",
            view_count=100 * i,
            monthly_likes=110 - (i * 5),  # 100, 95, 90, ..., 15
            monthly_dislikes=5,
        )
        clips.append(clip)

    test_db.add_all(clips)
    await test_db.commit()

    for clip in clips:
        await test_db.refresh(clip)

    return clips


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession):
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        role="USER",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture(scope="session")
def settings():
    """Get test settings"""
    return get_settings()


# Pytest markers
def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "concurrent: Concurrent/race condition tests")
    config.addinivalue_line("markers", "slow: Slow tests")
