"""
Leaderboard API endpoints for retrieving rankings and performance data.

Four main endpoints:
1. GET /api/v1/leaderboard/current - Current top 10 for this month
2. GET /api/v1/leaderboard/history/{month} - Archived top 10 for a specific month
3. GET /api/v1/leaderboard/clip/{id}/snapshots - Historical snapshots for a clip
4. GET /api/v1/leaderboard/trends - Trending clips (biggest rank improvement)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.cache_provider import get_cache_provider, LeaderboardCache
from backend.models import (
    Clip,
    LeaderboardSnapshot,
    LeaderboardMonthlySummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/leaderboard", tags=["leaderboard"])


def get_current_month() -> str:
    """Get current month in YYYY-MM format."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


@router.get("/current")
async def get_current_leaderboard(
    db: AsyncSession = Depends(get_db),
    cache: LeaderboardCache = Depends(get_cache_provider),
) -> Dict[str, Any]:
    """
    Get current top 10 clips for this month.

    Results are cached and updated every 5 seconds by background job.

    Returns:
        {
            "month_key": "2026-03",
            "clips": [
                {
                    "rank": 1,
                    "clip_id": 42,
                    "title": "Amazing gameplay",
                    "creator": "streamer_name",
                    "likes": 450,
                    "score": 400,
                    "thumbnail_url": "https://..."
                },
                ...
            ]
        }
    """
    current_month = get_current_month()

    # ==================================================================
    # STEP 1: Try cache first
    # ==================================================================
    cached_top_10 = await cache.get_top_10(current_month)
    if cached_top_10:
        logger.debug(f"Returning cached leaderboard for {current_month}")
        return {
            "month_key": current_month,
            "clips": cached_top_10,
        }

    logger.debug(f"Cache miss for {current_month}, querying database")

    # ==================================================================
    # STEP 2: Query database if not cached
    # ==================================================================
    try:
        result = await db.execute(
            select(Clip)
            .where(
                (Clip.month_key == current_month)
                & (Clip.monthly_likes > 0)
            )
            # Order by net score (likes - dislikes) to match tasks.py job
            .order_by((Clip.monthly_likes - Clip.monthly_dislikes).desc())
            .limit(10)
        )
        clips = result.scalars().all()
    except Exception as e:
        logger.error(f"Error querying leaderboard: {e}")
        return {
            "month_key": current_month,
            "clips": [],
        }

    if not clips:
        logger.info(f"No clips found for {current_month}")
        return {
            "month_key": current_month,
            "clips": [],
        }

    # ==================================================================
    # STEP 3: Format response — score = net (likes - dislikes)
    # ==================================================================
    formatted_clips = [
        {
            "rank": idx + 1,
            "clip_id": clip.id,
            "title": clip.title,
            "creator": clip.creator_name,
            "likes": clip.monthly_likes,
            "score": clip.monthly_likes - clip.monthly_dislikes,
            "thumbnail_url": clip.thumbnail_url,
        }
        for idx, clip in enumerate(clips)
    ]

    # ==================================================================
    # STEP 4: Cache for next request
    # ==================================================================
    await cache.set_top_10(current_month, formatted_clips)

    return {
        "month_key": current_month,
        "clips": formatted_clips,
    }


@router.get("/history/{month_key}")
async def get_historical_leaderboard(
    month_key: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get archived top 10 for a specific month (frozen end-of-month rankings).

    Args:
        month_key: Month in YYYY-MM format (e.g., "2026-02")

    Returns:
        {
            "month_key": "2026-02",
            "final_ranking": [...],
            "total_clips": 42,
            "total_votes": 1234,
            "total_unique_voters": 156,
            "top_clip_id": 42,
            "top_clip_score": 400
        }

        OR empty response if no data for this month:
        {
            "month_key": "2026-02",
            "final_ranking": [],
            "total_votes": 0,
            "total_unique_voters": 0,
            "top_clip_id": null,
            "top_clip_score": null,
            "month_end_date": null
        }
    """
    # ==================================================================
    # STEP 1: Query leaderboard_monthly_summary
    # ==================================================================
    try:
        result = await db.execute(
            select(LeaderboardMonthlySummary).where(
                LeaderboardMonthlySummary.snapshot_month == month_key,
            )
        )
        summary = result.scalar_one_or_none()
    except Exception as e:
        logger.error(
            f"Error querying leaderboard_monthly_summary for {month_key}: {e}",
            exc_info=True,
        )
        # Return empty response instead of crashing
        return {
            "month_key": month_key,
            "final_ranking": [],
            "total_votes": 0,
            "total_unique_voters": 0,
            "top_clip_id": None,
            "top_clip_score": None,
            "month_end_date": None,
        }

    # If no summary exists, return empty response
    if not summary:
        logger.debug(f"No leaderboard summary found for {month_key}, returning empty")
        return {
            "month_key": month_key,
            "final_ranking": [],
            "total_votes": 0,
            "total_unique_voters": 0,
            "top_clip_id": None,
            "top_clip_score": None,
            "month_end_date": None,
        }

    logger.debug(f"Retrieved historical leaderboard for {month_key}")

    return {
        "month_key": month_key,
        "final_ranking": summary.final_ranking or [],
        "total_votes": summary.total_votes or 0,
        "total_unique_voters": summary.total_unique_voters or 0,
        "top_clip_id": summary.top_clip_id,
        "top_clip_score": summary.top_clip_score,
        "month_end_date": summary.month_end_date.isoformat()
        if summary.month_end_date
        else None,
    }


@router.get("/clip/{clip_id}/snapshots")
async def get_clip_snapshots(
    clip_id: int,
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Get historical snapshots for a clip (for hype/performance graphs).

    Returns snapshots in chronological order showing rank, score, likes/dislikes over time.

    Args:
        clip_id: Clip ID
        hours: Number of hours of history to retrieve (default: 24)

    Returns:
        [
            {
                "timestamp": "2026-03-27T15:34:21Z",
                "rank": 5,
                "score": 320,
                "likes": 370,
                "dislikes": 50
            },
            ...
        ]
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    # ==================================================================
    # STEP 1: Query snapshots
    # ==================================================================
    result = await db.execute(
        select(LeaderboardSnapshot)
        .where(LeaderboardSnapshot.snapshot_timestamp >= cutoff_time)
        .order_by(LeaderboardSnapshot.snapshot_timestamp)
    )
    snapshots = result.scalars().all()

    if not snapshots:
        logger.debug(f"No snapshots found for clip {clip_id}")
        return []

    # ==================================================================
    # STEP 2: Extract clip data from JSONB rankings
    # ==================================================================
    clip_snapshots = []
    for snapshot in snapshots:
        # snapshot.ranking is a list of clip dicts from the top 10
        for clip_data in snapshot.ranking:
            if clip_data["clip_id"] == clip_id:
                clip_snapshots.append(
                    {
                        "timestamp": snapshot.snapshot_timestamp.isoformat(),
                        "rank": clip_data["rank"],
                        "score": clip_data["score"],
                        "likes": clip_data["likes"],
                        "dislikes": clip_data.get(
                            "dislikes", 0
                        ),  # May not be in all versions
                    }
                )
                break

    logger.debug(f"Retrieved {len(clip_snapshots)} snapshots for clip {clip_id}")

    return clip_snapshots


@router.get("/trends")
async def get_trending_clips(
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get trending clips - those with biggest rank improvement in last N hours.

    Clips that climbed from lower ranks to higher positions are "trending".

    Args:
        hours: Time window for trend calculation (default: 24)

    Returns:
        {
            "time_window_hours": 24,
            "trending": [
                {
                    "clip_id": 12,
                    "title": "Epic moment",
                    "creator": "streamer",
                    "rank_improvement": 8,
                    "current_rank": 2,
                    "earliest_rank": 10,
                    "current_score": 385,
                    "earliest_score": 150,
                    "thumbnail_url": "..."
                },
                ...
            ]
        }
    """
    current_month = get_current_month()
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    # ==================================================================
    # STEP 1: Get all snapshots in time window
    # ==================================================================
    result = await db.execute(
        select(LeaderboardSnapshot)
        .where(
            (LeaderboardSnapshot.snapshot_month == current_month)
            & (LeaderboardSnapshot.snapshot_timestamp >= cutoff_time)
        )
        .order_by(LeaderboardSnapshot.snapshot_timestamp)
    )
    snapshots = result.scalars().all()

    if not snapshots or len(snapshots) < 2:
        logger.debug("Not enough snapshots for trending calculation")
        return {
            "time_window_hours": hours,
            "trending": [],
        }

    # ==================================================================
    # STEP 2: Extract earliest and latest rankings
    # ==================================================================
    earliest_ranking = snapshots[0].ranking
    latest_ranking = snapshots[-1].ranking

    # Build maps for easy lookup
    earliest_map = {c["clip_id"]: c for c in earliest_ranking}
    latest_map = {c["clip_id"]: c for c in latest_ranking}

    # ==================================================================
    # STEP 3: Calculate improvements for clips that appear in both
    # ==================================================================
    trending_list = []
    for clip_id, latest_data in latest_map.items():
        if clip_id in earliest_map:
            earliest_data = earliest_map[clip_id]
            rank_improvement = (
                earliest_data["rank"] - latest_data["rank"]
            )  # Negative = better (moved up)

            trending_list.append(
                {
                    "clip_id": clip_id,
                    "title": latest_data.get("title", ""),
                    "creator": latest_data.get("creator", ""),
                    "thumbnail_url": latest_data.get("thumbnail_url"),
                    "rank_improvement": rank_improvement,
                    "current_rank": latest_data["rank"],
                    "earliest_rank": earliest_data["rank"],
                    "current_score": latest_data["score"],
                    "earliest_score": earliest_data["score"],
                }
            )

    # ==================================================================
    # STEP 4: Sort by rank improvement (biggest climbers first)
    # ==================================================================
    trending_list.sort(
        key=lambda x: x["rank_improvement"],
        reverse=True,  # Biggest climbers first
    )

    logger.debug(f"Found {len(trending_list)} trending clips")

    return {
        "time_window_hours": hours,
        "trending": trending_list[:20],  # Return top 20 trending
    }
