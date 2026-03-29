"""fix_clips_defaults_and_slug_length

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-29 00:00:00.000000

No-op: clips defaults (created_at, month_key) and twitch_clip_id VARCHAR(255) are
already defined in 2f969c1594d2_initial_schema for fresh DBs.

"""
from typing import Sequence, Union

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
