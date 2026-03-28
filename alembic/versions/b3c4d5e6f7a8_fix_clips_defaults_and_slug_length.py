"""fix_clips_defaults_and_slug_length

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-29 00:00:00.000000

Three fixes that make clip INSERTs reliable:

1. clips.created_at had no DB-level DEFAULT. SQLAlchemy emits INSERT without
   that column when server_default is set on the model, expecting Postgres to
   fill it in. Without the default every clip INSERT silently fails →
   _resolve_clip always returns None → vote endpoint always returns 404.

2. clips.twitch_clip_id was VARCHAR(50). Some Twitch slugs exceed 50 chars;
   widened to VARCHAR(255) to match the model and prevent truncation errors.

3. clips.month_key had no DB-level DEFAULT. Added to match model server_default.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add DB-level DEFAULT so SQLAlchemy's server_default actually works
    op.execute("ALTER TABLE clips ALTER COLUMN created_at SET DEFAULT now()")
    op.execute("ALTER TABLE clips ALTER COLUMN month_key SET DEFAULT to_char(now(), 'YYYY-MM')")

    # Widen twitch_clip_id from VARCHAR(50) to VARCHAR(255)
    op.alter_column(
        "clips",
        "twitch_clip_id",
        existing_type=sa.String(50),
        type_=sa.String(255),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "clips",
        "twitch_clip_id",
        existing_type=sa.String(255),
        type_=sa.String(50),
        existing_nullable=False,
    )
    op.execute("ALTER TABLE clips ALTER COLUMN month_key DROP DEFAULT")
    op.execute("ALTER TABLE clips ALTER COLUMN created_at DROP DEFAULT")
