"""Leaderboard clip performance model for tracking entry/exit events."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class LeaderboardClipPerformance(Base):
    """Per-clip performance tracking (entry/exit events per month)."""

    __tablename__ = "leaderboard_clip_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    clip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_month: Mapped[str] = mapped_column(
        String(7), nullable=False, index=True
    )  # YYYY-MM
    entered_top_10_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    exited_top_10_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    peak_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    peak_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_time_in_top_10: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Seconds
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_leaderboard_clip_performance_clip_id", "clip_id"),
        Index("ix_leaderboard_clip_performance_month", "snapshot_month"),
        UniqueConstraint(
            "clip_id",
            "snapshot_month",
            name="uq_leaderboard_clip_performance_clip_month",
        ),
    )

    def __repr__(self) -> str:
        return f"<LeaderboardClipPerformance(clip_id={self.clip_id}, month={self.snapshot_month}, peak_rank={self.peak_rank})>"
