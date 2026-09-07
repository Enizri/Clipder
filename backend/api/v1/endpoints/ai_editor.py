import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.clip_queue import append_export_mark, parse_export_flag
from backend.api.v1.deps import get_current_user
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.models import User, UserClipHistory
from backend.schemas.clip_history import (
    AnalyzeClipResponse,
    ClipHistoryCreate,
    ClipHistoryResponse,
    DeleteHistoryResponse,
    UploadClipRequest,
    UploadClipResponse,
    UserClipHistoryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai-editor", tags=["ai-editor"])

ANALYZE_SYSTEM_PROMPT = """You analyze Twitch clips for YouTube Shorts and TikTok.
Return ONLY valid JSON with these keys:
- transcript: a short spoken-style recap (1-3 sentences)
- score: a number from 0 to 1 for viral potential
- title: a YouTube Shorts / TikTok ready title
- description: a YouTube/TikTok ready description
No markdown, no extra keys."""


class ExportStatusResponse(BaseModel):
    status: str
    message: str
    marked_for_export: bool = True


async def _load_queue_entry(
    db: AsyncSession, user_id: int, clip_id: str
) -> UserClipHistory:
    result = await db.execute(
        select(UserClipHistory).where(
            (UserClipHistory.clip_id == clip_id)
            & (UserClipHistory.user_id == user_id)
        )
    )
    entry = result.scalars().first()
    if not entry:
        raise HTTPException(status_code=404, detail="Clip not found in your queue")
    return entry


def _demo_analysis(
    title: str, channel: str, existing_description: Optional[str]
) -> AnalyzeClipResponse:
    """Deterministic fallback so GIF recording works without GROQ_API_KEY."""
    cleaned = (title or "Untitled clip").strip() or "Untitled clip"
    digest = hashlib.md5(cleaned.encode("utf-8"), usedforsecurity=False).hexdigest()
    score = round(int(digest[:2], 16) / 255.0, 2)
    transcript = (
        f"Here's the vibe from {channel}: {cleaned}. "
        "Short, punchy recap ready for Shorts and TikTok."
    )
    new_title = cleaned if len(cleaned) <= 80 else cleaned[:77] + "..."
    existing = (existing_description or "").strip()
    description = existing or (
        f"{cleaned} — clipped from {channel}. #shorts #twitch #fyp"
    )
    return AnalyzeClipResponse(
        transcript=transcript,
        score=score,
        title=new_title,
        description=description,
    )


def _parse_analysis_payload(
    content: str, fallback: AnalyzeClipResponse
) -> AnalyzeClipResponse:
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return fallback
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return fallback
    if not isinstance(data, dict):
        return fallback

    transcript = str(data.get("transcript") or fallback.transcript).strip()
    title = str(data.get("title") or fallback.title).strip()
    description = str(data.get("description") or fallback.description).strip()
    raw_score = data.get("score", fallback.score)
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = fallback.score
    score = max(0.0, min(1.0, round(score, 4)))
    return AnalyzeClipResponse(
        transcript=transcript or fallback.transcript,
        score=score,
        title=title or fallback.title,
        description=description or fallback.description,
    )


async def _generate_analysis(
    title: str, channel: str, existing_description: Optional[str]
) -> AnalyzeClipResponse:
    fallback = _demo_analysis(title, channel, existing_description)
    groq_api_key = get_settings().groq_api_key
    if not groq_api_key:
        logger.info("GROQ_API_KEY missing; returning demo clip analysis")
        return fallback

    user_msg = (
        f'Clip title: "{title}"\n'
        f"Channel: {channel}\n"
        f"Existing description: {existing_description or '(none)'}\n\n"
        "Return JSON with transcript, score, title, and description."
    )
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": get_settings().groq_chat_model,
                    "messages": [
                        {"role": "system", "content": ANALYZE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
                timeout=15.0,
            )
            if response.status_code != 200:
                logger.error(
                    "Groq API error: %s - %s",
                    response.status_code,
                    response.text,
                )
                return fallback
            data = response.json()
            ai_content = data["choices"][0]["message"]["content"]
            return _parse_analysis_payload(ai_content, fallback)
    except httpx.RequestError as exc:
        logger.error("Groq API request error: %s", exc)
        return fallback
    except Exception as exc:
        logger.error("Unexpected Groq analysis error: %s", exc)
        return fallback


def _append_edit_action(
    entry: UserClipHistory,
    action: str,
    before: Optional[str],
    after: Optional[str],
) -> None:
    actions: List[Dict[str, Any]] = []
    if entry.edit_history:
        try:
            parsed = json.loads(entry.edit_history)
            if isinstance(parsed, list):
                actions = parsed
        except json.JSONDecodeError:
            actions = []
    actions.append(
        {
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "before": before,
            "after": after,
        }
    )
    entry.edit_history = json.dumps(actions)
    entry.last_edited_at = datetime.now(timezone.utc)


async def _analyze_and_save(entry: UserClipHistory) -> AnalyzeClipResponse:
    analysis = await _generate_analysis(
        title=entry.clip_title,
        channel=entry.clip_channel,
        existing_description=entry.clip_description,
    )
    before_title = entry.edited_title or entry.clip_title
    entry.clip_description = analysis.transcript
    entry.edited_title = analysis.title
    _append_edit_action(
        entry,
        action="analyzed",
        before=before_title,
        after=analysis.title,
    )
    return analysis


def _queued_upload_message(platforms: List[str]) -> str:
    labels: List[str] = []
    if "youtube_shorts" in platforms:
        labels.append("YouTube Shorts")
    if "tiktok" in platforms:
        labels.append("TikTok")
    if not labels:
        queued_for = "export"
    elif len(labels) == 1:
        queued_for = labels[0]
    else:
        queued_for = f"{labels[0]} and {labels[1]}"
    return (
        f"Queued for {queued_for}. Live upload adapters are not connected."
    )


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


@router.post(
    "/history/clip/{clip_id}/analyze", response_model=AnalyzeClipResponse
)
async def analyze_queued_clip(
    clip_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyzeClipResponse:
    """Analyze a queued clip for title, description, recap, and score.

    Uses Groq when GROQ_API_KEY is set; otherwise returns a deterministic
    demo analysis derived from the clip title.
    """
    entry = await _load_queue_entry(db, current_user.id, clip_id)
    analysis = await _analyze_and_save(entry)
    await db.commit()
    return analysis


@router.post(
    "/history/clip/{clip_id}/upload", response_model=UploadClipResponse
)
async def upload_queued_clip(
    clip_id: str,
    request: UploadClipRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadClipResponse:
    """Queue a playground clip for YouTube Shorts and/or TikTok.

    Engine upload adapters are stubs; this does not report a live publish.
    Runs analyze first when the clip has no transcript yet.
    """
    entry = await _load_queue_entry(db, current_user.id, clip_id)
    if not (entry.clip_description or "").strip():
        await _analyze_and_save(entry)

    already = parse_export_flag(entry.edit_history)
    if not already:
        append_export_mark(entry)
    await db.commit()

    platforms = list(request.platforms)
    youtube_id = "yt_id_mock" if "youtube_shorts" in platforms else None
    tiktok_queued = "tiktok" in platforms
    return UploadClipResponse(
        status="queued",
        youtube=youtube_id,
        tiktok=tiktok_queued,
        message=_queued_upload_message(platforms),
    )
