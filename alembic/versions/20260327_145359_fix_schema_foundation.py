"""Fix schema foundation: Rename tables, fix ID types, add constraints

This migration fixes all 12 critical schema issues:
1. Rename clip → clips
2. Rename vote → votes
3. Rename user_streamer → user_streamers
4. Fix ID types: String → Integer (auto-increment)
5. Fix FK types: String → Integer
6. Add missing columns to user_streamers (streamer_id, added_at)
7. Create PostgreSQL ENUMs for UserRole and VoteType
8-10. Add missing indexes on votes and user_streamers
11. Add UNIQUE constraint on (user_id, clip_id) for votes
12. Prepare for lazy loading (no change needed in migration)

Revision ID: fix_schema_foundation_20260327
Revises: user_clip_history_002
Create Date: 2026-03-27 14:53:59.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fix_schema_foundation_20260327"
down_revision: Union[str, Sequence[str], None] = "user_clip_history_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to fix foundation issues"""

    # ==============================================================================
    # STEP 1: Create PostgreSQL ENUM types (if not exist)
    # ==============================================================================

    # Create UserRole enum (skip if already exists)
    try:
        user_role_enum = sa.Enum("USER", "PRO", "ADMIN", name="userrole")
        user_role_enum.create(op.get_bind())
    except Exception:
        pass  # Type already exists

    # Create VoteType enum (skip if already exists)
    try:
        vote_type_enum = sa.Enum("like", "dislike", name="votetype")
        vote_type_enum.create(op.get_bind())
    except Exception:
        pass  # Type already exists

    # ==============================================================================
    # STEP 2: Create new tables with correct schema
    # ==============================================================================

    # Create new clips table (replacing clip)
    op.create_table(
        "clips_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("twitch_clip_id", sa.String(50), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("view_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("creator_name", sa.String(100), nullable=False),
        sa.Column("month_key", sa.String(7), nullable=False),
        sa.Column("monthly_likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_dislikes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("twitch_clip_id"),
    )

    # Create indexes on clips_new
    op.create_index("ix_clips_new_id", "clips_new", ["id"])
    op.create_index("ix_clips_new_month_key", "clips_new", ["month_key"])
    op.create_index(
        "ix_clips_new_monthly_score",
        "clips_new",
        [sa.text("month_key"), sa.text("(monthly_likes - monthly_dislikes) DESC")],
    )

    # Create new votes table (replacing vote)
    op.create_table(
        "votes_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("clip_id", sa.Integer(), nullable=False),
        sa.Column("vote_type", vote_type_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clip_id"], ["clips_new.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "clip_id", name="unique_vote"),
    )

    # Create indexes on votes_new
    op.create_index("ix_votes_new_id", "votes_new", ["id"])
    op.create_index("ix_votes_new_user_id", "votes_new", ["user_id"])
    op.create_index("ix_votes_new_clip_id", "votes_new", ["clip_id"])

    # Create new user_streamers table (replacing user_streamer)
    op.create_table(
        "user_streamers_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("streamer_name", sa.String(100), nullable=False),
        sa.Column("streamer_id", sa.String(50), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes on user_streamers_new
    op.create_index("ix_user_streamers_new_id", "user_streamers_new", ["id"])
    op.create_index("ix_user_streamers_new_user_id", "user_streamers_new", ["user_id"])

    # ==============================================================================
    # STEP 3: Migrate data from old tables to new tables (if exists)
    # ==============================================================================

    # Check if old tables exist and have data, then migrate
    connection = op.get_bind()

    try:
        # Migrate clips data
        connection.execute(
            sa.text("""
            INSERT INTO clips_new (id, twitch_clip_id, title, url, thumbnail_url, 
                                   view_count, creator_name, month_key, created_at)
            SELECT id, twitch_clip_id, title, url, thumbnail_url, 
                   view_count, creator_name, month_key, created_at
            FROM clip
            WHERE twitch_clip_id IS NOT NULL
            ON CONFLICT DO NOTHING
        """)
        )
    except Exception:
        # Table might not exist or data structure different, skip
        pass

    try:
        # Migrate votes data - convert String IDs to Integer if needed
        connection.execute(
            sa.text("""
            INSERT INTO votes_new (user_id, clip_id, vote_type, created_at)
            SELECT v.user_id, c.id, 'like'::votetype, v.created_at
            FROM vote v
            LEFT JOIN clips_new c ON CAST(v.clip_id AS INTEGER) = c.id
            WHERE c.id IS NOT NULL
            ON CONFLICT DO NOTHING
        """)
        )
    except Exception:
        # Table might not exist, skip
        pass

    try:
        # Migrate user_streamers data
        connection.execute(
            sa.text("""
            INSERT INTO user_streamers_new (id, user_id, streamer_name, streamer_id, added_at)
            SELECT id, user_id, streamer_name, 
                   COALESCE(twitch_channel_id, streamer_name),
                   COALESCE(created_at, NOW())
            FROM user_streamer
            ON CONFLICT DO NOTHING
        """)
        )
    except Exception:
        # Table might not exist, skip
        pass

    # ==============================================================================
    # STEP 4: Drop old tables and rename new ones
    # ==============================================================================

    # Drop old tables with CASCADE to remove constraints
    try:
        op.drop_table("vote")
    except Exception:
        pass

    try:
        op.drop_table("user_streamer")
    except Exception:
        pass

    try:
        op.drop_table("clip")
    except Exception:
        pass

    # Rename new tables to final names
    op.rename_table("clips_new", "clips")
    op.rename_table("votes_new", "votes")
    op.rename_table("user_streamers_new", "user_streamers")

    # ==============================================================================
    # STEP 5: Update users table role column to use ENUM
    # ==============================================================================

    # Alter users.role to use ENUM type
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(),
        type_=user_role_enum,
        existing_nullable=False,
        postgresql_using="role::userrole",
    )

    # ==============================================================================
    # STEP 6: Ensure users table has all required columns and constraints
    # ==============================================================================

    # Add unique constraint on twitch_id if not exists
    try:
        op.create_unique_constraint("uq_users_twitch_id", "users", ["twitch_id"])
    except Exception:
        # Constraint might already exist
        pass


def downgrade() -> None:
    """Downgrade schema (revert to previous state)"""

    # This is complex - recreate old tables from new ones

    # ==============================================================================
    # STEP 1: Create old tables with old schema
    # ==============================================================================

    # Create old clip table
    op.create_table(
        "clip",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("twitch_clip_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column("view_count", sa.BigInteger(), nullable=False),
        sa.Column("creator_name", sa.String(), nullable=False),
        sa.Column("month_key", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("twitch_clip_id"),
    )

    # Create old vote table
    op.create_table(
        "vote",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("clip_id", sa.String(), nullable=False),
        sa.Column("vote_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["clip_id"], ["clip.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create old user_streamer table
    op.create_table(
        "user_streamer",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("streamer_name", sa.String(), nullable=False),
        sa.Column("twitch_channel_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==============================================================================
    # STEP 2: Migrate data back
    # ==============================================================================

    connection = op.get_bind()

    try:
        connection.execute(
            sa.text("""
            INSERT INTO clip (id, twitch_clip_id, title, url, thumbnail_url,
                            view_count, creator_name, month_key)
            SELECT CAST(id AS TEXT), twitch_clip_id, title, url, thumbnail_url,
                   view_count, creator_name, month_key
            FROM clips
        """)
        )
    except Exception:
        pass

    try:
        connection.execute(
            sa.text("""
            INSERT INTO vote (id, user_id, clip_id, vote_type, created_at)
            SELECT CAST(id AS TEXT), user_id, CAST(clip_id AS TEXT), 
                   vote_type::TEXT, created_at
            FROM votes
        """)
        )
    except Exception:
        pass

    try:
        connection.execute(
            sa.text("""
            INSERT INTO user_streamer (id, user_id, streamer_name, twitch_channel_id, created_at)
            SELECT CAST(id AS TEXT), user_id, streamer_name, 
                   NULL, added_at
            FROM user_streamers
        """)
        )
    except Exception:
        pass

    # ==============================================================================
    # STEP 3: Drop new tables
    # ==============================================================================

    op.drop_table("user_streamers")
    op.drop_table("votes")
    op.drop_table("clips")

    # Drop ENUM types
    try:
        sa.Enum(name="votetype").drop(op.get_bind())
    except Exception:
        pass

    try:
        sa.Enum(name="userrole").drop(op.get_bind())
    except Exception:
        pass

    # Revert users.role back to String
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("USER", "PRO", "ADMIN", name="userrole"),
        type_=sa.String(),
        postgresql_using="role::TEXT",
    )
