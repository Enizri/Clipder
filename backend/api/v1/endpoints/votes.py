from datetime import datetime, timezone
from typing import Dict, Any
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.core.database import get_db
from backend.models import User, Clip, Vote, VoteType
from backend.api.v1.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/votes", tags=["votes"])


def get_month_key() -> str:
    """Get current month in YYYY-MM format."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


@router.post("/like/{clip_id}")
async def like_clip(
    clip_id: int = Path(..., gt=0, description="Clip ID must be positive"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Like a clip and increment monthly_likes counter.

    Returns immediately without waiting for leaderboard update.
    The 5-second job will recalculate rankings and broadcast via WebSocket.

    Args:
        clip_id: Clip ID to like
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response with current vote status and counter
    """
    # ==================================================================
    # STEP 1: Get the clip
    # ==================================================================
    clip = await db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    # ==================================================================
    # STEP 2: Check if user already voted
    # ==================================================================
    existing_vote = await db.execute(
        select(Vote).where(
            (Vote.user_id == current_user.id) & (Vote.clip_id == clip_id)
        )
    )
    existing = existing_vote.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400, detail="You have already voted on this clip"
        )

    # ==================================================================
    # STEP 3: Create vote record
    # ==================================================================
    vote = Vote(user_id=current_user.id, clip_id=clip_id, vote_type=VoteType.LIKE)
    db.add(vote)

    # ==================================================================
    # STEP 4: Update monthly_likes counter
    # ==================================================================
    clip.monthly_likes += 1

    await db.commit()

    logger.info(f"User {current_user.id} liked clip {clip_id}")

    # ==================================================================
    # STEP 5: Return immediate response
    # ==================================================================
    # Don't wait for leaderboard job - it will run in 5 seconds
    return {
        "status": "success",
        "current_likes": clip.monthly_likes,
        "current_dislikes": clip.monthly_dislikes,
        "current_score": clip.monthly_likes - clip.monthly_dislikes,
    }


@router.post("/dislike/{clip_id}")
async def dislike_clip(
    clip_id: int = Path(..., gt=0, description="Clip ID must be positive"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Dislike a clip and increment monthly_dislikes counter.

    Returns immediately without waiting for leaderboard update.
    The 5-second job will recalculate rankings and broadcast via WebSocket.

    Args:
        clip_id: Clip ID to dislike
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response with current vote status and counter
    """
    # ==================================================================
    # STEP 1: Get the clip
    # ==================================================================
    clip = await db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    # ==================================================================
    # STEP 2: Check if user already voted
    # ==================================================================
    existing_vote = await db.execute(
        select(Vote).where(
            (Vote.user_id == current_user.id) & (Vote.clip_id == clip_id)
        )
    )
    existing = existing_vote.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400, detail="You have already voted on this clip"
        )

    # ==================================================================
    # STEP 3: Create vote record
    # ==================================================================
    vote = Vote(user_id=current_user.id, clip_id=clip_id, vote_type=VoteType.DISLIKE)
    db.add(vote)

    # ==================================================================
    # STEP 4: Update monthly_dislikes counter
    # ==================================================================
    clip.monthly_dislikes += 1

    await db.commit()

    logger.info(f"User {current_user.id} disliked clip {clip_id}")

    # ==================================================================
    # STEP 5: Return immediate response
    # ==================================================================
    # Don't wait for leaderboard job - it will run in 5 seconds
    return {
        "status": "success",
        "current_likes": clip.monthly_likes,
        "current_dislikes": clip.monthly_dislikes,
        "current_score": clip.monthly_likes - clip.monthly_dislikes,
    }


@router.get("/clip/{clip_id}/votes")
async def get_clip_votes(
    clip_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get vote counts for a clip.

    Args:
        clip_id: Clip ID
        db: Database session

    Returns:
        Vote counts (likes, dislikes, score)
    """
    clip = await db.get(Clip, clip_id)

    if not clip:
        return {
            "clip_id": clip_id,
            "likes": 0,
            "dislikes": 0,
            "score": 0,
        }

    return {
        "clip_id": clip_id,
        "likes": clip.monthly_likes,
        "dislikes": clip.monthly_dislikes,
        "score": clip.monthly_likes - clip.monthly_dislikes,
    }


@router.post("/clip/{clip_id}/vote")
async def vote_on_clip(
    clip_id: int,
    vote_type: str = Query(..., description="Vote type: 'like' or 'dislike'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Unified vote endpoint supporting both like and dislike via query parameter.

    This endpoint is called by the frontend:
    - POST /api/v1/votes/clip/{clip_id}/vote?vote_type=like
    - POST /api/v1/votes/clip/{clip_id}/vote?vote_type=dislike

    Args:
        clip_id: Clip ID to vote on
        vote_type: 'like' or 'dislike'
        current_user: Current authenticated user
        db: Database session

    Returns:
        Vote status with current clip score
    """
    if vote_type not in ("like", "dislike"):
        raise HTTPException(
            status_code=400, detail="vote_type must be 'like' or 'dislike'"
        )

    # ==================================================================
    # STEP 1: Get the clip
    # ==================================================================
    clip = await db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    # ==================================================================
    # STEP 2: Check if user already voted
    # ==================================================================
    existing_vote = await db.execute(
        select(Vote).where(
            (Vote.user_id == current_user.id) & (Vote.clip_id == clip_id)
        )
    )
    existing = existing_vote.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400, detail="You have already voted on this clip"
        )

    # ==================================================================
    # STEP 3: Create vote record and update counters
    # ==================================================================
    vote_enum = VoteType.LIKE if vote_type == "like" else VoteType.DISLIKE
    vote = Vote(user_id=current_user.id, clip_id=clip_id, vote_type=vote_enum)
    db.add(vote)

    if vote_type == "like":
        clip.monthly_likes += 1
    else:
        clip.monthly_dislikes += 1

    await db.commit()

    logger.info(f"User {current_user.id} voted {vote_type} on clip {clip_id}")

    # ==================================================================
    # STEP 4: Return response matching frontend expectations
    # ==================================================================
    return {
        "status": "success",
        "clip_id": clip_id,
        "current_likes": clip.monthly_likes,
        "current_dislikes": clip.monthly_dislikes,
        "current_score": clip.monthly_likes - clip.monthly_dislikes,
    }
