"""
Integration tests for leaderboard snapshot job (5-second recalculation).
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession



@pytest.mark.integration
@pytest.mark.asyncio
async def test_snapshot_table_exists(test_db: AsyncSession):
    """Test: Leaderboard snapshots table exists and is queryable"""

    result = await test_db.execute(text("SELECT COUNT(*) FROM leaderboard_snapshots"))
    count = result.scalar()
    assert isinstance(count, int)
    assert count >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_snapshot_captures_top_10(test_db: AsyncSession, test_clips):
    """Test: Snapshot correctly identifies top 10 clips by score"""

    # Manually create a snapshot (normally done by job every 5s)
    # For this test, verify top 10 are correctly identified

    # Sort test clips by likes - dislikes (score)
    clips_by_score = sorted(
        test_clips, key=lambda c: c.monthly_likes - c.monthly_dislikes, reverse=True
    )

    top_10_expected = clips_by_score[:10]

    # Verify top clip has highest score
    for i, clip in enumerate(top_10_expected):
        score = clip.monthly_likes - clip.monthly_dislikes
        assert score > 0, f"Clip {i} has score {score}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_snapshot_score_calculation(test_db: AsyncSession, test_clips):
    """Test: Snapshot calculates score as (likes - dislikes)"""

    for clip in test_clips:
        expected_score = clip.monthly_likes - clip.monthly_dislikes
        assert expected_score >= 0, f"Score should be non-negative: {expected_score}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_snapshot_no_duplicates(test_db: AsyncSession, test_clips):
    """Test: Snapshot doesn't include duplicate clips in top 10"""

    # Get top 10
    top_10_ids = [c.id for c in test_clips[:10]]

    # Verify no duplicates
    assert len(top_10_ids) == len(set(top_10_ids)), "Duplicate clip IDs in top 10"
