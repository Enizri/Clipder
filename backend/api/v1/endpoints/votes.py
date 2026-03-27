from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.core.database import get_db
from backend.core.state import get_state, AppState
from backend.models import User, Clip, Vote, VoteType, UserRole
from backend.api.v1.deps import get_current_user

router = APIRouter(prefix="/api/votes", tags=["votes"])


def get_month_key() -> str:
    return datetime.utcnow().strftime("%Y-%m")


@router.post("/clip/{twitch_clip_id}/vote")
async def vote_clip(
    twitch_clip_id: str,
    vote_type: str = "like",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    state: AppState = Depends(get_state),
) -> Dict[str, Any]:
    if vote_type not in ["like", "dislike"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vote type must be 'like' or 'dislike'",
        )

    result = await db.execute(select(Clip).where(Clip.twitch_clip_id == twitch_clip_id))
    clip = result.scalar_one_or_none()

    if not clip:
        metadata = state.clip_metadata_store.get(twitch_clip_id, {})
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found"
            )

        clip = Clip(
            twitch_clip_id=twitch_clip_id,
            title=metadata.get("title", "Unknown"),
            url=metadata.get("url", ""),
            thumbnail_url=metadata.get("thumbnail_url"),
            view_count=metadata.get("view_count", 0),
            creator_name=metadata.get("creator_name", "Unknown"),
            month_key=get_month_key(),
            score=0.0,
        )
        db.add(clip)
        await db.commit()
        await db.refresh(clip)

    existing_vote = await db.execute(
        select(Vote).where(Vote.user_id == current_user.id, Vote.clip_id == clip.id)
    )
    existing = existing_vote.scalar_one_or_none()

    if existing:
        if existing.vote_type == VoteType.LIKE and vote_type == "like":
            await db.delete(existing)
            await db.commit()
        else:
            existing.vote_type = (
                VoteType.LIKE if vote_type == "like" else VoteType.DISLIKE
            )
            await db.commit()
    else:
        vote = Vote(
            user_id=current_user.id,
            clip_id=clip.id,
            vote_type=VoteType.LIKE if vote_type == "like" else VoteType.DISLIKE,
        )
        db.add(vote)
        await db.commit()

    likes_count = await db.execute(
        select(func.count(Vote.id)).where(
            Vote.clip_id == clip.id, Vote.vote_type == VoteType.LIKE
        )
    )
    current_score = likes_count.scalar() or 0

    state.clip_scores[twitch_clip_id] = current_score

    leaderboard = await state.get_leaderboard()
    await state.ws_manager.broadcast(
        {"type": "leaderboard_update", "data": leaderboard[:10]}
    )

    return {
        "status": "voted",
        "current_score": current_score,
    }


@router.get("/clip/{twitch_clip_id}/votes")
async def get_clip_votes(
    twitch_clip_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    result = await db.execute(select(Clip).where(Clip.twitch_clip_id == twitch_clip_id))
    clip = result.scalar_one_or_none()

    if not clip:
        return {"likes": 0, "dislikes": 0, "user_vote": None}

    likes_count = await db.execute(
        select(func.count(Vote.id)).where(
            Vote.clip_id == clip.id, Vote.vote_type == VoteType.LIKE
        )
    )
    dislikes_count = await db.execute(
        select(func.count(Vote.id)).where(
            Vote.clip_id == clip.id, Vote.vote_type == VoteType.DISLIKE
        )
    )

    return {
        "likes": likes_count.scalar() or 0,
        "dislikes": dislikes_count.scalar() or 0,
    }
