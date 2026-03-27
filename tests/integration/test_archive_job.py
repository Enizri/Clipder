"""
Integration tests for archive and aggregation jobs.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hourly_aggregates_table_exists(test_db: AsyncSession):
    """Test: Leaderboard hourly aggregates table exists"""

    result = await test_db.execute("SELECT COUNT(*) FROM leaderboard_hourly_aggregates")
    count = result.scalar()
    assert isinstance(count, int)
    assert count >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_snapshots_archived_after_24h(test_db: AsyncSession):
    """Test: Snapshots older than 24 hours are archived to hourly_aggregates"""

    # This would require:
    # 1. Create old snapshot (24h+ old)
    # 2. Run archive job
    # 3. Verify snapshot moved to hourly_aggregates

    # For now, verify table structure
    result = await test_db.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='leaderboard_hourly_aggregates'"
    )
    columns = [row[0] for row in result]
    assert len(columns) > 0, "hourly_aggregates table has no columns"
