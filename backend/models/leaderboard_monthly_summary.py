"""Leaderboard monthly summary model for frozen end-of-month rankings."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Float, DateTime, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class LeaderboardMonthlySummary(Base):
    """Frozen end-of-month rankings archive (JSONB)."""

    __tablename__ = "leaderboard_monthly_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    snapshot_month: Mapped[str] = mapped_column(
        String(7), nullable=False, index=True, unique=True
    )  # YYYY-MM
    final_ranking: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )  # [{rank, clip_id, score, title, creator_name, thumbnail_url, final_likes, final_dislikes}]
    total_votes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_unique_voters: Mapped[int] = mapped_column(Integer, nullable=False)
    top_clip_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    top_clip_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    month_end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_leaderboard_monthly_summary_month", "snapshot_month"),
        UniqueConstraint("snapshot_month", name="uq_leaderboard_monthly_summary_month"),
    )

    def __repr__(self) -> str:
        return f"<LeaderboardMonthlySummary(month={self.snapshot_month}, top_clip_id={self.top_clip_id}, top_score={self.top_clip_score})>"
