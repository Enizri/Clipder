"""initial_schema

Revision ID: 2f969c1594d2
Revises:
Create Date: 2026-03-28 16:54:39.252767

Creates the full schema on an empty PostgreSQL database (FK-safe order).
Later revisions a1b2c3d4e5f6 and b3c4d5e6f7a8 are no-ops: their effects are included here.

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2f969c1594d2"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums used by ORM models (idempotent for dev re-runs)
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('USER', 'PRO', 'ADMIN');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE votetype AS ENUM ('like', 'dislike');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    userrole = postgresql.ENUM("USER", "PRO", "ADMIN", name="userrole", create_type=False)
    votetype = postgresql.ENUM("like", "dislike", name="votetype", create_type=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "role",
            userrole,
            nullable=False,
            server_default=sa.text("'USER'::userrole"),
        ),
        sa.Column(
            "is_pro",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "free_studio_clips_generated",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("twitch_id", sa.String(length=50), nullable=True),
        sa.Column("twitch_username", sa.String(length=50), nullable=True),
        sa.Column("twitch_access_token", sa.String(length=500), nullable=True),
        sa.Column("twitch_refresh_token", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_twitch_id"), "users", ["twitch_id"], unique=True)

    op.create_table(
        "clips",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("twitch_clip_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("view_count", sa.BigInteger(), nullable=False),
        sa.Column("creator_name", sa.String(length=100), nullable=False),
        sa.Column(
            "month_key",
            sa.String(length=7),
            server_default=sa.text("to_char(now(), 'YYYY-MM')"),
            nullable=False,
        ),
        sa.Column(
            "monthly_likes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "monthly_dislikes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("current_rank", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("twitch_clip_id"),
    )
    op.create_index(op.f("ix_clips_id"), "clips", ["id"], unique=False)
    op.create_index(op.f("ix_clips_month_key"), "clips", ["month_key"], unique=False)

    op.create_table(
        "user_streamers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("streamer_name", sa.String(length=100), nullable=False),
        sa.Column("streamer_id", sa.String(length=50), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_streamers_id"), "user_streamers", ["id"], unique=False)
    op.create_index(
        op.f("ix_user_streamers_user_id"), "user_streamers", ["user_id"], unique=False
    )

    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("clip_id", sa.Integer(), nullable=False),
        sa.Column("vote_type", votetype, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clip_id"], ["clips.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "clip_id", name="unique_vote"),
    )
    op.create_index(op.f("ix_votes_id"), "votes", ["id"], unique=False)
    op.create_index(op.f("ix_votes_user_id"), "votes", ["user_id"], unique=False)
    op.create_index(op.f("ix_votes_clip_id"), "votes", ["clip_id"], unique=False)

    op.create_table(
        "user_clip_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("clip_id", sa.String(), nullable=False),
        sa.Column("clip_title", sa.String(), nullable=False),
        sa.Column("clip_url", sa.String(), nullable=False),
        sa.Column("clip_channel", sa.String(), nullable=False),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column("clip_description", sa.String(), nullable=True),
        sa.Column("clip_tags", sa.Text(), nullable=True),
        sa.Column("edited_title", sa.String(), nullable=True),
        sa.Column("chat_messages", sa.Text(), nullable=True),
        sa.Column("edit_history", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("last_edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_clip_history_id"), "user_clip_history", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_user_clip_history_user_id"), "user_clip_history", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_user_clip_history_clip_id"), "user_clip_history", ["clip_id"], unique=False
    )
    op.create_index(
        op.f("ix_user_clip_history_created_at"),
        "user_clip_history",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "leaderboard_monthly_summary",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_month", sa.String(length=7), nullable=False),
        sa.Column(
            "final_ranking",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("total_votes", sa.Integer(), nullable=False),
        sa.Column("total_unique_voters", sa.Integer(), nullable=False),
        sa.Column("top_clip_id", sa.Integer(), nullable=True),
        sa.Column("top_clip_score", sa.Float(), nullable=True),
        sa.Column("month_end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_month", name="uq_leaderboard_monthly_summary_month"),
    )
    op.create_index(
        op.f("ix_leaderboard_monthly_summary_id"),
        "leaderboard_monthly_summary",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_leaderboard_monthly_summary_month",
        "leaderboard_monthly_summary",
        ["snapshot_month"],
        unique=False,
    )
    op.create_table(
        "leaderboard_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_month", sa.String(length=7), nullable=False),
        sa.Column("snapshot_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ranking",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_leaderboard_snapshots_id"), "leaderboard_snapshots", ["id"], unique=False
    )
    op.create_index(
        "ix_leaderboard_snapshots_month",
        "leaderboard_snapshots",
        ["snapshot_month"],
        unique=False,
    )
    op.create_index(
        op.f("ix_leaderboard_snapshots_snapshot_month"),
        "leaderboard_snapshots",
        ["snapshot_month"],
        unique=False,
    )
    op.create_index(
        op.f("ix_leaderboard_snapshots_snapshot_timestamp"),
        "leaderboard_snapshots",
        ["snapshot_timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_leaderboard_snapshots_timestamp",
        "leaderboard_snapshots",
        ["snapshot_timestamp"],
        unique=False,
    )

    op.create_table(
        "clip_video_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("clip_id", sa.Integer(), nullable=False),
        sa.Column("video_url", sa.String(length=1000), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["clip_id"], ["clips.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_clip_video_cache_clip_id"), "clip_video_cache", ["clip_id"], unique=True
    )
    op.create_index(
        op.f("ix_clip_video_cache_id"), "clip_video_cache", ["id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_clip_video_cache_id"), table_name="clip_video_cache")
    op.drop_index(op.f("ix_clip_video_cache_clip_id"), table_name="clip_video_cache")
    op.drop_table("clip_video_cache")

    op.drop_index("ix_leaderboard_snapshots_timestamp", table_name="leaderboard_snapshots")
    op.drop_index(
        op.f("ix_leaderboard_snapshots_snapshot_timestamp"),
        table_name="leaderboard_snapshots",
    )
    op.drop_index(
        op.f("ix_leaderboard_snapshots_snapshot_month"),
        table_name="leaderboard_snapshots",
    )
    op.drop_index("ix_leaderboard_snapshots_month", table_name="leaderboard_snapshots")
    op.drop_index(op.f("ix_leaderboard_snapshots_id"), table_name="leaderboard_snapshots")
    op.drop_table("leaderboard_snapshots")

    op.drop_index(
        "ix_leaderboard_monthly_summary_month", table_name="leaderboard_monthly_summary"
    )
    op.drop_index(
        op.f("ix_leaderboard_monthly_summary_id"), table_name="leaderboard_monthly_summary"
    )
    op.drop_table("leaderboard_monthly_summary")

    op.drop_index(
        op.f("ix_user_clip_history_created_at"), table_name="user_clip_history"
    )
    op.drop_index(op.f("ix_user_clip_history_clip_id"), table_name="user_clip_history")
    op.drop_index(op.f("ix_user_clip_history_user_id"), table_name="user_clip_history")
    op.drop_index(op.f("ix_user_clip_history_id"), table_name="user_clip_history")
    op.drop_table("user_clip_history")

    op.drop_index(op.f("ix_votes_clip_id"), table_name="votes")
    op.drop_index(op.f("ix_votes_user_id"), table_name="votes")
    op.drop_index(op.f("ix_votes_id"), table_name="votes")
    op.drop_table("votes")

    op.drop_index(op.f("ix_user_streamers_user_id"), table_name="user_streamers")
    op.drop_index(op.f("ix_user_streamers_id"), table_name="user_streamers")
    op.drop_table("user_streamers")

    op.drop_index(op.f("ix_clips_month_key"), table_name="clips")
    op.drop_index(op.f("ix_clips_id"), table_name="clips")
    op.drop_table("clips")

    op.drop_index(op.f("ix_users_twitch_id"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS votetype")
    op.execute("DROP TYPE IF EXISTS userrole")
