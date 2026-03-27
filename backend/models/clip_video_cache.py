from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class ClipVideoCache(Base):
    """Cache for extracted video URLs to avoid repeated yt-dlp calls."""

    __tablename__ = "clip_video_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    clip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clips.id"), unique=True, index=True, nullable=False
    )
    video_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Metadata for cache invalidation if needed
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Add relationship back to clip if needed
    # clip: Mapped["Clip"] = relationship("Clip", back_populates="video_cache")
