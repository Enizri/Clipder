"""Per-user playground queue: liked clips a user can review or skip."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Clip, User, UserClipHistory

logger = logging.getLogger(__name__)


async def enqueue_liked_clip(
    db: AsyncSession, user: User, clip: Clip
) -> Tuple[UserClipHistory, bool]:
    """Add a clip to the user's playground queue if it is not already there.

    Returns (entry, created).
    """
    result = await db.execute(
        select(UserClipHistory).where(
            (UserClipHistory.user_id == user.id)
            & (UserClipHistory.clip_id == clip.twitch_clip_id)
        )
    )
    existing = result.scalars().first()
    if existing:
        return existing, False

    entry = UserClipHistory(
        id=str(uuid.uuid4()),
        user_id=user.id,
        clip_id=clip.twitch_clip_id,
        clip_title=clip.title,
        clip_url=clip.url,
        clip_channel=clip.creator_name,
        thumbnail_url=clip.thumbnail_url,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    logger.info(
        "Queued clip %s for user %s playground", clip.twitch_clip_id, user.id
    )
    return entry, True


def history_is_marked_for_export(entry: UserClipHistory) -> bool:
    if not entry.edit_history:
        return False
    try:
        actions = json.loads(entry.edit_history)
    except json.JSONDecodeError:
        return False
    if not isinstance(actions, list):
        return False
    return any(
        isinstance(item, dict) and item.get("action") == "marked_for_export"
        for item in actions
    )


def append_export_mark(entry: UserClipHistory) -> None:
    actions = []
    if entry.edit_history:
        try:
            parsed = json.loads(entry.edit_history)
            if isinstance(parsed, list):
                actions = parsed
        except json.JSONDecodeError:
            actions = []
    if any(
        isinstance(item, dict) and item.get("action") == "marked_for_export"
        for item in actions
    ):
        return
    actions.append(
        {
            "action": "marked_for_export",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "before": None,
            "after": "queued",
        }
    )
    entry.edit_history = json.dumps(actions)
    entry.last_edited_at = datetime.now(timezone.utc)


def parse_export_flag(edit_history: Optional[str]) -> bool:
    if not edit_history:
        return False
    try:
        actions = json.loads(edit_history)
    except json.JSONDecodeError:
        return False
    if not isinstance(actions, list):
        return False
    return any(
        isinstance(item, dict) and item.get("action") == "marked_for_export"
        for item in actions
    )
