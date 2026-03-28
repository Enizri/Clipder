"""twitch_only_auth

Revision ID: a1b2c3d4e5f6
Revises: 2f969c1594d2
Create Date: 2026-03-28 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "2f969c1594d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make email and password_hash nullable (Twitch-only auth)
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)

    # Drop unique constraint on email (multiple Twitch users won't have email)
    op.drop_index("ix_users_email", table_name="users", if_exists=True)

    # Add PRO tier columns
    op.add_column("users", sa.Column("is_pro", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column(
        "users",
        sa.Column("free_studio_clips_generated", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "free_studio_clips_generated")
    op.drop_column("users", "is_pro")
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
