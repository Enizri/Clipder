"""Leaderboard snapshot model for real-time 5-second tracking."""

from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class LeaderboardSnapshot(Base):
    """Real-time leaderboard snapshot (5-second intervals, 24h window)."""

    __tablename__ = "leaderboard_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    snapshot_month: Mapped[str] = mapped_column(
        String(7), nullable=False, index=True
    )  # YYYY-MM
    snapshot_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ranking: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )  # [{rank, clip_id, score, title, creator_name, thumbnail_url}]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_leaderboard_snapshots_month", "snapshot_month"),
        Index("ix_leaderboard_snapshots_timestamp", "snapshot_timestamp"),
    )

    def __repr__(self) -> str:
        return f"<LeaderboardSnapshot(id={self.id}, month={self.snapshot_month}, timestamp={self.snapshot_timestamp})>"
