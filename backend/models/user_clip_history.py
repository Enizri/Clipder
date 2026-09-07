import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class UserClipHistory(Base):
    """Stores clip history for PRO users in AI Editor with edits and chat."""

    __tablename__ = "user_clip_history"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    clip_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    clip_title: Mapped[str] = mapped_column(String, nullable=False)
    clip_url: Mapped[str] = mapped_column(String, nullable=False)
    clip_channel: Mapped[str] = mapped_column(String, nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    clip_description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # JSON array of string tags
    clip_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    edited_title: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # JSON array of {role, content, timestamp}
    chat_messages: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON array of {action, timestamp, before, after}
    edit_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )
    last_edited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship("User", backref="clip_history")  # type: ignore[name-defined]  # noqa: F821
