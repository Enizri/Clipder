import logging
from typing import List, Dict, Any, Set

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.core.twitch_oauth import TwitchOAuth
from backend.models import User, UserStreamer
from backend.api.v1.deps import get_current_user

router = APIRouter(prefix="/api/v1/following", tags=["following"])

twitch_oauth = TwitchOAuth()
logger = logging.getLogger(__name__)


async def sync_twitch_follows_for_user(db: AsyncSession, user: User) -> int:
    """
    Insert UserStreamer rows for Twitch channels this user follows on Twitch.
    Does not commit — caller commits. Idempotent with existing streamer_id rows.
    """
    if not user.twitch_id or not user.twitch_access_token:
        return 0

    follows = await twitch_oauth.get_user_follows(
        user.twitch_access_token,
        user.twitch_id,
    )

    result = await db.execute(
        select(UserStreamer.streamer_id).where(UserStreamer.user_id == user.id)
    )
    existing_streamer_ids = set(row[0] for row in result.all())

    added = 0
    for follow in follows:
        if follow["to_id"] not in existing_streamer_ids:
            streamer = UserStreamer(
                user_id=user.id,
                streamer_name=follow["to_name"],
                streamer_id=follow["to_id"],
                include_in_for_you=True,
            )
            db.add(streamer)
            added += 1

    return added


class StreamerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    streamer_name: str
    streamer_id: str
    include_in_for_you: bool = True


class ForYouSelectionRequest(BaseModel):
    """Exact set of Twitch user ids that should appear in For You (must be existing follows)."""

    streamer_ids: List[str] = Field(default_factory=list)


class AddStreamerRequest(BaseModel):
    streamer_name: str
    streamer_id: str


class TwitchFollowResponse(BaseModel):
    to_id: str
    to_name: str


class SearchChannelResponse(BaseModel):
    id: str
    name: str
    game_name: str
    is_live: bool


@router.get("", response_model=List[StreamerResponse])
async def get_user_streamers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[StreamerResponse]:
    """Get user's selected streamers"""
    result = await db.execute(
        select(UserStreamer).where(UserStreamer.user_id == current_user.id)
    )
    streamers = result.scalars().all()
    return [StreamerResponse.model_validate(s) for s in streamers]


@router.post("", response_model=StreamerResponse)
async def add_streamer(
    request: AddStreamerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamerResponse:
    """Add a streamer to user's list"""
    existing = await db.execute(
        select(UserStreamer).where(
            UserStreamer.user_id == current_user.id,
            UserStreamer.streamer_id == request.streamer_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streamer already in your list",
        )

    streamer = UserStreamer(
        user_id=current_user.id,
        streamer_name=request.streamer_name,
        streamer_id=request.streamer_id,
        include_in_for_you=True,
    )
    db.add(streamer)
    await db.commit()
    await db.refresh(streamer)
    return StreamerResponse.model_validate(streamer)


@router.delete("/{streamer_id}")
async def remove_streamer(
    streamer_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Remove a streamer from user's list"""
    result = await db.execute(
        select(UserStreamer).where(
            UserStreamer.user_id == current_user.id,
            UserStreamer.streamer_id == streamer_id,
        )
    )
    streamer = result.scalar_one_or_none()
    if not streamer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Streamer not found in your list",
        )

    await db.delete(streamer)
    await db.commit()
    return {"status": "removed"}


@router.get("/twitch/follows", response_model=List[TwitchFollowResponse])
async def get_twitch_follows(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[TwitchFollowResponse]:
    """Get user's Twitch follows (requires linked Twitch account)"""
    if not current_user.twitch_id or not current_user.twitch_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Twitch account not linked",
        )

    follows = await twitch_oauth.get_user_follows(
        current_user.twitch_access_token,
        current_user.twitch_id,
    )
    return [TwitchFollowResponse(**f) for f in follows]


@router.get("/search", response_model=List[SearchChannelResponse])
async def search_channels(
    q: str,
    current_user: User = Depends(get_current_user),
) -> List[SearchChannelResponse]:
    """Search for Twitch channels"""
    if not current_user.twitch_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Twitch account not linked",
        )

    channels = await twitch_oauth.search_channels(q, current_user.twitch_access_token)
    return [SearchChannelResponse.model_validate(c) for c in channels]


@router.post("/sync")
async def sync_with_twitch(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Sync user's streamers with their Twitch follows (same helper as post-OAuth)."""
    if not current_user.twitch_id or not current_user.twitch_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Twitch account not linked",
        )

    added = await sync_twitch_follows_for_user(db, current_user)
    await db.commit()
    return {"status": "synced", "added": added}


@router.put("/for-you", response_model=Dict[str, Any])
async def set_for_you_inclusion(
    body: ForYouSelectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Mark which followed channels are included in the For You feed. Omitted follows become excluded."""
    result = await db.execute(
        select(UserStreamer).where(UserStreamer.user_id == current_user.id)
    )
    rows = list(result.scalars().all())
    if not rows:
        return {"status": "ok", "included_count": 0}

    allowed: Set[str] = {r.streamer_id for r in rows}
    selected: Set[str] = {s for s in body.streamer_ids if s in allowed}
    for r in rows:
        r.include_in_for_you = r.streamer_id in selected
    await db.commit()
    return {"status": "ok", "included_count": sum(1 for r in rows if r.include_in_for_you)}
