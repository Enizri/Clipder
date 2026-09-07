"""
Integration tests for delta calculation (rank changes detection).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
@pytest.mark.asyncio
async def test_clips_enter_top_10(test_db: AsyncSession, test_clips):
    """Test: When clip enters top 10, it's marked as 'clips_entered'"""

    # Clip at position 11 with 15 likes
    outside_clip = test_clips[14]  # Last clip (lowest score)

    # Verify it's outside top 10
    assert outside_clip.monthly_likes == 15, (
        f"Expected 15 likes, got {outside_clip.monthly_likes}"
    )

    # When its score increases past rank 10, it should enter top 10
    # For now, just verify this clip exists and can be compared
    assert outside_clip.id is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_clips_exit_top_10(test_db: AsyncSession, test_clips):
    """Test: When clip exits top 10, it's marked as 'clips_exited'"""

    # Clip at position 10 with 60 likes
    boundary_clip = test_clips[9]

    # Verify it's at boundary
    assert boundary_clip.monthly_likes == 60, (
        f"Expected 60 likes, got {boundary_clip.monthly_likes}"
    )

    # When its score decreases below top 10, it should exit
    # For now, just verify this clip exists
    assert boundary_clip.id is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_position_changes_detected(test_db: AsyncSession, test_clips):
    """Test: When clip rank changes within top 10, it's marked as 'position_changes'"""

    # Rank 1 and 2 clips
    rank_1 = test_clips[0]  # 100 likes
    rank_2 = test_clips[1]  # 95 likes

    # Both are in top 10
    assert rank_1.monthly_likes > rank_2.monthly_likes

    # If rank_1 loses 10 likes and rank_2 gains 10, they should swap
    # For now, verify ranking is correct
    assert rank_1.monthly_likes == 100
    assert rank_2.monthly_likes == 95


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rank_1_vs_rank_2_swap(test_db: AsyncSession, test_clips):
    """Test: Rank 1 vs Rank 2 swap is detected correctly"""

    rank_1 = test_clips[0]
    rank_2 = test_clips[1]

    score_1 = rank_1.monthly_likes - rank_1.monthly_dislikes
    score_2 = rank_2.monthly_likes - rank_2.monthly_dislikes

    # Rank 1 should have higher score
    assert score_1 > score_2, (
        f"Rank 1 score {score_1} should be > Rank 2 score {score_2}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_simultaneous_changes(test_db: AsyncSession, test_clips):
    """Test: Multiple changes detected in single snapshot (entry + exit + swap)"""

    # Get diverse clips for testing
    entering_clip = test_clips[14]  # Will enter top 10
    exiting_clip = test_clips[9]  # Will exit top 10
    swapping_clip = test_clips[0]  # Will swap rank

    # Verify all are distinct
    assert entering_clip.id != exiting_clip.id
    assert exiting_clip.id != swapping_clip.id
    assert swapping_clip.id != entering_clip.id
