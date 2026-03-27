"""Add leaderboard tables for real-time ranking system.

Revision ID: 20260327_160000
Revises: 20260327_145359
Create Date: 2026-03-27 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Revision identifiers
revision = "20260327_160000"
down_revision = "fix_schema_foundation_20260327"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create leaderboard tables for real-time ranking and analytics."""

    # leaderboard_snapshots: Real-time tracking (5-second intervals, 24h window)
    op.create_table(
        "leaderboard_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_month", sa.String(7), nullable=False),  # Format: YYYY-MM
        sa.Column("snapshot_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ranking", postgresql.JSONB(), nullable=False
        ),  # Array of {rank, clip_id, score, title, creator_name, thumbnail_url}
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_leaderboard_snapshots_month", "snapshot_month"),
        sa.Index("ix_leaderboard_snapshots_timestamp", "snapshot_timestamp"),
    )

    # leaderboard_hourly_aggregates: Long-term archive (hourly compressed, unlimited history)
    op.create_table(
        "leaderboard_hourly_aggregates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_month", sa.String(7), nullable=False),  # Format: YYYY-MM
        sa.Column(
            "hour_start", sa.DateTime(timezone=True), nullable=False
        ),  # Start of hour (UTC)
        sa.Column(
            "ranking", postgresql.JSONB(), nullable=False
        ),  # Array of {rank, clip_id, score}
        sa.Column(
            "snapshot_count", sa.Integer(), nullable=False
        ),  # Number of 5-second snapshots in this hour
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_leaderboard_hourly_month", "snapshot_month"),
        sa.Index("ix_leaderboard_hourly_hour_start", "hour_start"),
        sa.UniqueConstraint(
            "snapshot_month", "hour_start", name="uq_leaderboard_hourly_month_hour"
        ),
    )

    # leaderboard_clip_performance: Per-clip performance tracking (entry/exit events)
    op.create_table(
        "leaderboard_clip_performance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("clip_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_month", sa.String(7), nullable=False),  # Format: YYYY-MM
        sa.Column("entered_top_10_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exited_top_10_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("peak_rank", sa.Integer(), nullable=True),
        sa.Column("peak_score", sa.Float(), nullable=True),
        sa.Column("total_time_in_top_10", sa.Integer(), nullable=True),  # Seconds
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clip_id"], ["clips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_leaderboard_clip_performance_clip_id", "clip_id"),
        sa.Index("ix_leaderboard_clip_performance_month", "snapshot_month"),
        sa.UniqueConstraint(
            "clip_id",
            "snapshot_month",
            name="uq_leaderboard_clip_performance_clip_month",
        ),
    )

    # leaderboard_monthly_summary: Frozen end-of-month rankings (JSONB archive)
    op.create_table(
        "leaderboard_monthly_summary",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_month", sa.String(7), nullable=False),  # Format: YYYY-MM
        sa.Column(
            "final_ranking", postgresql.JSONB(), nullable=False
        ),  # Array of {rank, clip_id, score, title, creator_name, thumbnail_url, final_likes, final_dislikes}
        sa.Column("total_votes", sa.Integer(), nullable=False),
        sa.Column("total_unique_voters", sa.Integer(), nullable=False),
        sa.Column("top_clip_id", sa.Integer(), nullable=True),
        sa.Column("top_clip_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("month_end_date", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_leaderboard_monthly_summary_month", "snapshot_month"),
        sa.UniqueConstraint(
            "snapshot_month", name="uq_leaderboard_monthly_summary_month"
        ),
    )


def downgrade() -> None:
    """Drop leaderboard tables."""
    op.drop_table("leaderboard_monthly_summary")
    op.drop_table("leaderboard_clip_performance")
    op.drop_table("leaderboard_hourly_aggregates")
    op.drop_table("leaderboard_snapshots")
