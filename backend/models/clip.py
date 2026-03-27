from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, DateTime, BigInteger, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.vote import Vote


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    twitch_clip_id: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    view_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    creator_name: Mapped[str] = mapped_column(String(100), nullable=False)
    month_key: Mapped[str] = mapped_column(
        String(7), index=True, nullable=False
    )  # e.g., "2026-03"
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    votes: Mapped[list["Vote"]] = relationship(
        "Vote", back_populates="clip", cascade="all, delete-orphan"
    )
