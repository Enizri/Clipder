"""
Background scheduler tasks for leaderboard maintenance and real-time updates.

Three main jobs:
1. Calculate top 10 rankings every 5 seconds
2. Archive old snapshots daily at midnight
3. Finalize month-end rankings on 1st of month at midnight
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, text
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from backend.core.cache_provider import get_cache_provider
from backend.core.state import ConnectionManager
from backend.core import database
from backend.models import (
    Clip,
    LeaderboardSnapshot,
    LeaderboardMonthlySummary,
)

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


# ==============================================================================
# JOB 1: Calculate Top 10 Rankings (Every 5 seconds)
# ==============================================================================


async def job_calculate_top_10(*, force_broadcast: bool = False) -> None:
    """
    Job 1: Calculate and update top 10 rankings every 5 seconds.

    - Fetch top 10 clips for current month
    - Compare with cached version
    - If changed, update cache and broadcast via WebSocket
    - Record snapshot in leaderboard_snapshots table when the ranking changes

    Args:
        force_broadcast: When True (e.g. immediately after a vote), always refresh
            cache + WebSocket so clients never miss a like-count update.
    """
    try:
        # Initialize database if needed
        if database.async_session_maker is None:
            database.init_database()

        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        cache = get_cache_provider()

        # Use global async_session_maker instead of creating new engine
        if database.async_session_maker is None:
            logger.warning("Database not initialized; skipping job_calculate_top_10")
            return

        async with database.async_session_maker() as db:
            # Check if table has required columns - skip if not ready
            try:
                result = await db.execute(
                    select(Clip)
                    .where(
                        (Clip.month_key == current_month)
                        & (Clip.monthly_likes > 0)
                    )
                    .order_by(
                        (Clip.monthly_likes - Clip.monthly_dislikes).desc(),
                        Clip.monthly_likes.desc(),
                        Clip.view_count.desc(),
                    )
                    .limit(10)
                )
                clips = result.scalars().all()
            except Exception as col_error:
                logger.warning(
                    f"Database schema not ready for job: {str(col_error)[:100]}"
                )
                return

            if not clips:
                # Leaderboard became empty but cache may still show old top 10 — sync clients + DB.
                prior_top = await cache.get_top_10(current_month)
                if prior_top:
                    rank_clear = await db.execute(
                        select(Clip).where(
                            Clip.month_key == current_month,
                            Clip.current_rank.is_not(None),
                        )
                    )
                    for clip_row in rank_clear.scalars():
                        clip_row.current_rank = None
                    await cache.set_top_10(current_month, [])
                    await db.commit()
                    connection_manager = ConnectionManager.get_instance()
                    await connection_manager.broadcast_leaderboard_changes(
                        {
                            "clips_entered": [],
                            "clips_exited": [
                                {"clip_id": c["clip_id"]} for c in prior_top
                            ],
                            "position_changes": [],
                            "top_10": [],
                        }
                    )
                    try:
                        db.add(
                            LeaderboardSnapshot(
                                snapshot_month=current_month,
                                snapshot_timestamp=datetime.now(timezone.utc),
                                ranking=[],
                            )
                        )
                        await db.commit()
                    except Exception as snap_error:
                        logger.error(
                            f"Failed to record empty leaderboard snapshot: {snap_error}",
                            exc_info=True,
                        )
                logger.debug("No clips with likes for month %s", current_month)
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

                # Find clips that changed position OR score (e.g. liked at rank #1)
                for new_clip in new_top_10:
                    for cached_clip in cached_top_10:
                        if new_clip["clip_id"] == cached_clip["clip_id"]:
                            rank_changed = new_clip["rank"] != cached_clip["rank"]
                            score_changed = new_clip["score"] != cached_clip.get("score")
                            if rank_changed or score_changed:
                                changes["position_changes"].append(
                                    {
                                        "clip_id": new_clip["clip_id"],
                                        "old_rank": cached_clip["rank"],
                                        "new_rank": new_clip["rank"],
                                        "score": new_clip["score"],
                                        "likes": new_clip["likes"],
                                    }
                                )
                                changed = True
                            break

            if force_broadcast:
                changed = True

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

                try:
                    snapshot = LeaderboardSnapshot(
                        snapshot_month=current_month,
                        snapshot_timestamp=datetime.now(timezone.utc),
                        ranking=new_top_10,
                    )
                    db.add(snapshot)
                    await db.commit()
                except Exception as snap_error:
                    logger.error(
                        f"Failed to record snapshot: {snap_error}", exc_info=True
                    )

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
        if database.async_session_maker is None:
            database.init_database()

        if database.async_session_maker is None:
            logger.warning("Database not initialized; skipping job_archive_snapshots")
            return

        async with database.async_session_maker() as db:
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
        if database.async_session_maker is None:
            database.init_database()

        now = datetime.now(timezone.utc)
        previous_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        current_month = now.strftime("%Y-%m")

        if database.async_session_maker is None:
            logger.warning("Database not initialized; skipping job_finalize_month_end")
            return

        async with database.async_session_maker() as db:
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
                from backend.models import Vote

                total_votes_result = await db.execute(
                    select(func.sum(Clip.monthly_likes + Clip.monthly_dislikes)).where(
                        Clip.month_key == previous_month
                    )
                )
                total_votes = total_votes_result.scalar() or 0

                # Count distinct users who voted on clips in the previous month
                unique_voters_result = await db.execute(
                    select(func.count(func.distinct(Vote.user_id))).where(
                        Vote.clip_id.in_(
                            select(Clip.id).where(Clip.month_key == previous_month)
                        )
                    )
                )
                total_unique_voters = unique_voters_result.scalar() or 0
            except Exception as stats_error:
                logger.warning(
                    f"Could not calculate statistics: {str(stats_error)[:100]}"
                )
                total_votes = 0
                total_unique_voters = 0

            # Insert monthly summary
            summary = LeaderboardMonthlySummary(
                snapshot_month=previous_month,
                final_ranking=final_ranking,
                total_votes=int(total_votes),
                total_unique_voters=int(total_unique_voters),
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
