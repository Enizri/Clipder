import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

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


@router.post("/history/save", response_model=ClipHistoryResponse)
async def save_clip_to_history(
    request: ClipHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a clip to user's AI Editor history (PRO only)."""

    # Check if user is PRO
    if current_user.role.value not in ["PRO", "ADMIN"]:
        raise HTTPException(
            status_code=403, detail="Only PRO users can save clips to history"
        )

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
    """Get all saved clips for current user."""

    # Check if user is PRO
    if current_user.role.value not in ["PRO", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only PRO users can view history")

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
    """Delete a clip from user's history by clip_id."""

    # Check if user is PRO
    if current_user.role.value not in ["PRO", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only PRO users can manage history")

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
    """Clear all history entries for current user."""

    # Check if user is PRO
    if current_user.role.value not in ["PRO", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only PRO users can manage history")

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

    # Check if user is PRO
    if current_user.role.value not in ["PRO", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only PRO users can manage history")

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
