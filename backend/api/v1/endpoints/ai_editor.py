import uuid
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.clip_queue import append_export_mark, parse_export_flag
from backend.api.v1.deps import get_current_user
from backend.core.database import get_db
from backend.models import User, UserClipHistory
from backend.schemas.clip_history import (
    ClipHistoryCreate,
    ClipHistoryResponse,
    UserClipHistoryResponse,
    DeleteHistoryResponse,
)

router = APIRouter(prefix="/api/v1/ai-editor", tags=["ai-editor"])


class ExportStatusResponse(BaseModel):
    status: str
    message: str
    marked_for_export: bool = True


@router.post("/history/save", response_model=ClipHistoryResponse)
async def save_clip_to_history(
    request: ClipHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a clip to the logged-in user's playground queue."""

    existing = await db.execute(
        select(UserClipHistory).where(
            (UserClipHistory.user_id == current_user.id)
            & (UserClipHistory.clip_id == request.clip_id)
        )
    )
    prior = existing.scalars().first()
    if prior:
        return ClipHistoryResponse.model_validate(prior)


    # Create new history entry
    history_id = str(uuid.uuid4())
    history_entry = UserClipHistory(
        id=history_id,
        user_id=current_user.id,
        clip_id=request.clip_id,
        clip_title=request.clip_title,
        clip_url=request.clip_url,
        clip_channel=request.clip_channel,
        thumbnail_url=request.thumbnail_url,
        clip_description=request.clip_description,
        clip_tags=json.dumps(request.clip_tags) if request.clip_tags else None,
        edited_title=request.edited_title,
        chat_messages=json.dumps([m.model_dump() for m in request.chat_messages])
        if request.chat_messages
        else None,
        edit_history=json.dumps([e.model_dump() for e in request.edit_history])
        if request.edit_history
        else None,
        created_at=datetime.now(timezone.utc),
    )

    db.add(history_entry)
    await db.commit()
    await db.refresh(history_entry)

    return ClipHistoryResponse.model_validate(history_entry)


@router.get("/history", response_model=UserClipHistoryResponse)
async def get_user_clip_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's playground queue."""

    result = await db.execute(
        select(UserClipHistory)
        .where(UserClipHistory.user_id == current_user.id)
        .order_by(UserClipHistory.created_at.desc())
    )

    history_entries = result.scalars().all()

    return UserClipHistoryResponse(
        history=[
            ClipHistoryResponse.model_validate(entry) for entry in history_entries
        ],
        total=len(history_entries),
    )


@router.delete("/history/clip/{clip_id}", response_model=DeleteHistoryResponse)
async def delete_clip_from_history(
    clip_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a clip from the user's playground queue (skip export)."""

    # Find and delete all entries for this clip by current user
    result = await db.execute(
        select(UserClipHistory).where(
            (UserClipHistory.clip_id == clip_id)
            & (UserClipHistory.user_id == current_user.id)
        )
    )

    entries = result.scalars().all()
    if not entries:
        return DeleteHistoryResponse(status="success", message="Clip not found")

    for entry in entries:
        await db.delete(entry)

    await db.commit()

    return DeleteHistoryResponse(
        status="success",
        message=f"Removed {len(entries)} clip(s) from history",
    )


@router.delete("/history/clear-all", response_model=DeleteHistoryResponse)
async def clear_all_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear the current user's playground queue."""

    await db.execute(
        delete(UserClipHistory).where(UserClipHistory.user_id == current_user.id)
    )
    await db.commit()

    return DeleteHistoryResponse(
        status="success",
        message="All history cleared",
    )


@router.delete("/history/{history_id}", response_model=DeleteHistoryResponse)
async def delete_history_entry(
    history_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific history entry by its UUID."""

    # Find and delete the entry
    result = await db.execute(
        select(UserClipHistory).where(
            (UserClipHistory.id == history_id)
            & (UserClipHistory.user_id == current_user.id)
        )
    )

    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")

    await db.delete(entry)
    await db.commit()

    return DeleteHistoryResponse(
        status="success",
        message="Clip removed from history",
    )


@router.post(
    "/history/clip/{clip_id}/export", response_model=ExportStatusResponse
)
async def mark_clip_for_export(
    clip_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExportStatusResponse:
    """Mark a queued clip for later multi-platform export.

    Upload adapters in the engine are not connected; this records the user's
    decision so they can skip or keep clips independently of the leaderboard vote.
    """
    result = await db.execute(
        select(UserClipHistory).where(
            (UserClipHistory.clip_id == clip_id)
            & (UserClipHistory.user_id == current_user.id)
        )
    )
    entry = result.scalars().first()
    if not entry:
        raise HTTPException(status_code=404, detail="Clip not found in your queue")

    already = parse_export_flag(entry.edit_history)
    if not already:
        append_export_mark(entry)
        await db.commit()

    return ExportStatusResponse(
        status="queued",
        message=(
            "Marked for export. YouTube/TikTok upload is not connected yet; "
            "the clip stays in your queue."
        ),
        marked_for_export=True,
    )
