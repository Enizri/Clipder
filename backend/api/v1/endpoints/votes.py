import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from backend.core.database import get_db
from backend.models import User, Clip, Vote, VoteType
from backend.api.v1.deps import get_current_user
from backend.core.tasks import job_calculate_top_10

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/votes", tags=["votes"])


async def _resolve_clip(clip_id: str, db: AsyncSession) -> Optional[Clip]:
    """Dual-lookup: try integer PK first, then fall back to twitch_clip_id slug."""
    try:
        pk = int(clip_id)
        clip = await db.get(Clip, pk)
        if clip:
            return clip
    except ValueError:
        pass

    result = await db.execute(select(Clip).where(Clip.twitch_clip_id == clip_id))
    return result.scalar_one_or_none()


@router.post("/clip/{clip_id}/vote")
async def vote_on_clip(
    clip_id: str,
    vote_type: str = Query(..., description="Vote type: 'like' or 'dislike'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Unified vote endpoint — accepts both integer PKs and Twitch clip slugs.

    Called by the frontend:
    - POST /api/v1/votes/clip/{id}/vote?vote_type=like
    - POST /api/v1/votes/clip/{id}/vote?vote_type=dislike
    """
    if vote_type not in ("like", "dislike"):
        raise HTTPException(status_code=400, detail="vote_type must be 'like' or 'dislike'")

    clip = await _resolve_clip(clip_id, db)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    vote_enum = VoteType.LIKE if vote_type == "like" else VoteType.DISLIKE
    vote = Vote(user_id=current_user.id, clip_id=clip.id, vote_type=vote_enum)
    db.add(vote)

    if vote_type == "like":
        clip.monthly_likes += 1
    else:
        clip.monthly_dislikes += 1

    try:
        await db.commit()
    except IntegrityError:
        # User already voted on this clip — roll back and return current counts as success.
        # This keeps swiping idempotent: duplicate votes are silently accepted.
        await db.rollback()
        fresh = await db.get(Clip, clip.id)
        if not fresh:
            raise HTTPException(status_code=404, detail="Clip not found")
        logger.debug("User %s re-voted %s on clip %s (idempotent)", current_user.id, vote_type, clip.id)
        try:
            await job_calculate_top_10(force_broadcast=True)
        except Exception as e:
            logger.warning("Leaderboard refresh failed after idempotent vote: %s", e)
        return {
            "status": "success",
            "clip_id": fresh.id,
            "current_likes": fresh.monthly_likes,
            "current_dislikes": fresh.monthly_dislikes,
            "current_score": fresh.monthly_likes - fresh.monthly_dislikes,
        }

    logger.info("User %s voted %s on clip %s", current_user.id, vote_type, clip.id)

    # Trigger immediate leaderboard refresh — scheduler is fallback every 5s
    try:
        await job_calculate_top_10(force_broadcast=True)
    except Exception as e:
        logger.warning("Leaderboard refresh failed after vote: %s", e)

    return {
        "status": "success",
        "clip_id": clip.id,
        "current_likes": clip.monthly_likes,
        "current_dislikes": clip.monthly_dislikes,
        "current_score": clip.monthly_likes - clip.monthly_dislikes,
    }


@router.get("/clip/{clip_id}/votes")
async def get_clip_votes(
    clip_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get current vote counts for a clip."""
    clip = await _resolve_clip(clip_id, db)

    if not clip:
        return {"clip_id": clip_id, "likes": 0, "dislikes": 0, "score": 0}

    return {
        "clip_id": clip.id,
        "likes": clip.monthly_likes,
        "dislikes": clip.monthly_dislikes,
        "score": clip.monthly_likes - clip.monthly_dislikes,
    }
