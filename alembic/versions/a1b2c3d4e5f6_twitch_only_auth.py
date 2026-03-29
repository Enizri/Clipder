"""twitch_only_auth

Revision ID: a1b2c3d4e5f6
Revises: 2f969c1594d2
Create Date: 2026-03-28 18:00:00.000000

No-op: Twitch-only nullable email/password, PRO columns, and dropped email
unique index are already applied in 2f969c1594d2_initial_schema for fresh DBs.

"""
from typing import Sequence, Union

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "2f969c1594d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema changes folded into 2f969c1594d2 — keep revision for existing alembic_version stamps.
    pass


def downgrade() -> None:
    pass
