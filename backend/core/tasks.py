"""
Background scheduler tasks for leaderboard maintenance and real-time updates.

Three main jobs:
1. Calculate top 10 rankings every 5 seconds
2. Archive old snapshots daily at midnight
3. Finalize month-end rankings on 1st of month at midnight
"""

import logging
from datetime import datetime, timedelta, time, timezone
from typing import Dict, List, Any

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from backend.core.cache_provider import get_cache_provider
from backend.core.state import ConnectionManager
from backend.core.database import async_session_maker, init_database
from backend.models import (
    Clip,
    LeaderboardSnapshot,
    LeaderboardClipPerformance,
    LeaderboardMonthlySummary,
)

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


# ==============================================================================
# JOB 1: Calculate Top 10 Rankings (Every 5 seconds)
# ==============================================================================


async def job_calculate_top_10() -> None:
    """
    Job 1: Calculate and update top 10 rankings every 5 seconds.

    - Fetch top 10 clips for current month
    - Compare with cached version
    - If changed, update cache and broadcast via WebSocket
    - Record snapshot in leaderboard_snapshots table
    """
    try:
        # Initialize database if needed
        if async_session_maker is None:
            init_database()

        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        cache = get_cache_provider()

        # Use global async_session_maker instead of creating new engine
        async with async_session_maker() as db:
            # Check if table has required columns - skip if not ready
            try:
                result = await db.execute(
                    select(Clip)
                    .where(Clip.month_key == current_month)
                    .order_by((Clip.monthly_likes - Clip.monthly_dislikes).desc())
                    .limit(10)
                )
                clips = result.scalars().all()
            except Exception as col_error:
                logger.warning(
                    f"Database schema not ready for job: {str(col_error)[:100]}"
                )
                return

            if not clips:
                logger.debug(f"No clips found for month {current_month}")
                return

            # Format new top 10
            new_top_10 = [
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

            # Compare with cached version
            cached_top_10 = await cache.get_top_10(current_month)
            changed = False
            changes = {
                "clips_entered": [],
                "clips_exited": [],
                "position_changes": [],
            }

            if cached_top_10 is None:
                # No cache yet, this is the first run
                changed = True
                logger.info(f"Initial top 10 calculation for {current_month}")
            else:
                # Compare rankings
                cached_clip_ids = {c["clip_id"] for c in cached_top_10}
                new_clip_ids = {c["clip_id"] for c in new_top_10}

                # Find clips that entered top 10
                for clip in new_top_10:
                    if clip["clip_id"] not in cached_clip_ids:
                        changes["clips_entered"].append(clip)
                        changed = True

                # Find clips that exited top 10
                for cached_clip in cached_top_10:
                    if cached_clip["clip_id"] not in new_clip_ids:
                        changes["clips_exited"].append(
                            {"clip_id": cached_clip["clip_id"]}
                        )
                        changed = True

                # Find clips that changed position
                for new_clip in new_top_10:
                    for cached_clip in cached_top_10:
                        if new_clip["clip_id"] == cached_clip["clip_id"]:
                            if new_clip["rank"] != cached_clip["rank"]:
                                changes["position_changes"].append(
                                    {
                                        "clip_id": new_clip["clip_id"],
                                        "old_rank": cached_clip["rank"],
                                        "new_rank": new_clip["rank"],
                                        "score": new_clip["score"],
                                    }
                                )
                                changed = True
                            break

            # Update cache if changed
            if changed:
                await cache.set_top_10(current_month, new_top_10)
                logger.info(
                    f"Top 10 for {current_month} updated ({len(changes['clips_entered']) + len(changes['position_changes'])} changes)"
                )

                # Update current_rank on Clip model BEFORE broadcast
                for clip_data in new_top_10:
                    clip = await db.get(Clip, clip_data["clip_id"])
                    if clip:
                        clip.current_rank = clip_data["rank"]

                await db.commit()

                # Broadcast changes via WebSocket AFTER commit
                connection_manager = ConnectionManager.get_instance()
                changes["top_10"] = new_top_10
                await connection_manager.broadcast_leaderboard_changes(changes)

            # Record snapshot in leaderboard_snapshots AFTER broadcast
            try:
                snapshot = LeaderboardSnapshot(
                    snapshot_month=current_month,
                    snapshot_timestamp=datetime.now(timezone.utc),
                    ranking=new_top_10,
                )
                db.add(snapshot)
                await db.commit()
            except Exception as snap_error:
                logger.error(f"Failed to record snapshot: {snap_error}", exc_info=True)

    except Exception as e:
        logger.error(f"Error in job_calculate_top_10: {e}", exc_info=True)


# ==============================================================================
# JOB 2: Archive Old Snapshots (Daily at midnight UTC)
# ==============================================================================


async def job_archive_snapshots() -> None:
    """
    Job 2: Archive old snapshots daily at midnight.

    - Find snapshots older than 24 hours
    - Delete old snapshots
    """
    try:
        logger.info("Starting snapshot archival job")

        # Initialize database if needed
        if async_session_maker is None:
            init_database()

        async with async_session_maker() as db:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

            # Find and delete old snapshots
            result = await db.execute(
                select(LeaderboardSnapshot).where(
                    LeaderboardSnapshot.snapshot_timestamp < cutoff_time
                )
            )
            old_snapshots = result.scalars().all()

            if old_snapshots:
                logger.info(f"Deleting {len(old_snapshots)} old snapshots")
                for snapshot in old_snapshots:
                    await db.delete(snapshot)
                await db.commit()
            else:
                logger.debug("No old snapshots to archive")

    except Exception as e:
        logger.error(f"Error in job_archive_snapshots: {e}", exc_info=True)


# ==============================================================================
# JOB 3: Finalize Month-End Rankings (1st of month at midnight UTC)
# ==============================================================================


async def job_finalize_month_end() -> None:
    """
    Job 3: Archive and finalize rankings at end of month.

    - Get top 10 clips from previous month
    - Insert into leaderboard_monthly_summary
    - Reset current month clips' counters
    """
    try:
        logger.info("Starting month-end finalization job")

        # Initialize database if needed
        if async_session_maker is None:
            init_database()

        now = datetime.now(timezone.utc)
        previous_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        current_month = now.strftime("%Y-%m")

        async with async_session_maker() as db:
            # Get top 10 from previous month
            result = await db.execute(
                select(Clip)
                .where(Clip.month_key == previous_month)
                .order_by((Clip.monthly_likes - Clip.monthly_dislikes).desc())
                .limit(10)
            )
            top_clips = result.scalars().all()

            if not top_clips:
                logger.warning(f"No clips found for previous month {previous_month}")
                return

            # Format final ranking
            final_ranking = [
                {
                    "rank": idx + 1,
                    "clip_id": clip.id,
                    "title": clip.title,
                    "creator": clip.creator_name,
                    "final_likes": clip.monthly_likes,
                    "score": clip.monthly_likes - clip.monthly_dislikes,
                    "thumbnail_url": clip.thumbnail_url,
                }
                for idx, clip in enumerate(top_clips)
            ]

            # Calculate statistics
            try:
                all_clips_result = await db.execute(
                    select(func.count(Clip.id)).where(Clip.month_key == previous_month)
                )
                total_clips = all_clips_result.scalar() or 0

                # Count total votes for the month
                total_votes_result = await db.execute(
                    select(func.sum(Clip.monthly_likes + Clip.monthly_dislikes)).where(
                        Clip.month_key == previous_month
                    )
                )
                total_votes = total_votes_result.scalar() or 0
            except Exception as stats_error:
                logger.warning(
                    f"Could not calculate statistics: {str(stats_error)[:100]}"
                )
                total_clips = 0
                total_votes = 0

            # Insert monthly summary
            summary = LeaderboardMonthlySummary(
                snapshot_month=previous_month,
                final_ranking=final_ranking,
                total_votes=int(total_votes),
                top_clip_id=top_clips[0].id,
                top_clip_score=top_clips[0].monthly_likes
                - top_clips[0].monthly_dislikes,
                month_end_date=now.replace(day=1) - timedelta(seconds=1),
            )
            db.add(summary)

            # Reset current month counters
            await db.execute(
                text("""
                    UPDATE clips 
                    SET monthly_likes = 0, monthly_dislikes = 0, current_rank = NULL
                    WHERE month_key = :current_month
                """),
                {"current_month": current_month},
            )

            await db.commit()
            logger.info(f"Finalized rankings for {previous_month}")

    except Exception as e:
        logger.error(f"Error in job_finalize_month_end: {e}", exc_info=True)


# ==============================================================================
# SCHEDULER MANAGEMENT
# ==============================================================================


def start_scheduler() -> None:
    """Start the background scheduler with all jobs."""
    try:
        scheduler = get_scheduler()

        if scheduler.running:
            logger.info("Scheduler already running")
            return

        # Job 1: Calculate top 10 every 5 seconds
        scheduler.add_job(
            job_calculate_top_10,
            trigger=IntervalTrigger(seconds=5),
            id="calculate_top_10",
            name="Calculate Top 10 Rankings",
            replace_existing=True,
        )

        # Job 2: Archive snapshots daily at midnight UTC
        scheduler.add_job(
            job_archive_snapshots,
            trigger=CronTrigger(hour=0, minute=0),
            id="archive_snapshots",
            name="Archive Old Snapshots",
            replace_existing=True,
        )

        # Job 3: Finalize month-end on 1st at midnight UTC
        scheduler.add_job(
            job_finalize_month_end,
            trigger=CronTrigger(day=1, hour=0, minute=0),
            id="finalize_month_end",
            name="Finalize Month-End Rankings",
            replace_existing=True,
        )

        scheduler.start()
        logger.info("Scheduler started with 3 jobs")

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    try:
        scheduler = get_scheduler()
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}", exc_info=True)
