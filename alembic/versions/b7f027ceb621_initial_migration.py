"""Initial migration

Revision ID: b7f027ceb621
Revises: 
Create Date: 2026-03-25 18:37:25.384361

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7f027ceb621'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create user table (plural to match the User model)
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('twitch_id', sa.String(50), nullable=True),
        sa.Column('twitch_username', sa.String(50), nullable=True),
        sa.Column('twitch_access_token', sa.String(500), nullable=True),
        sa.Column('twitch_refresh_token', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('twitch_id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create clip table
    op.create_table(
        'clip',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('twitch_clip_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('thumbnail_url', sa.String(), nullable=True),
        sa.Column('view_count', sa.BigInteger(), nullable=False),
        sa.Column('creator_name', sa.String(), nullable=False),
        sa.Column('month_key', sa.String(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('twitch_clip_id')
    )
    op.create_index(op.f('ix_clip_id'), 'clip', ['id'], unique=False)
    op.create_index(op.f('ix_clip_month_key'), 'clip', ['month_key'], unique=False)

    # Create vote table
    op.create_table(
        'vote',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('clip_id', sa.String(), nullable=False),
        sa.Column('vote_type', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['clip_id'], ['clip.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vote_id'), 'vote', ['id'], unique=False)

    # Create user_streamer table
    op.create_table(
        'user_streamer',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('streamer_name', sa.String(), nullable=False),
        sa.Column('twitch_channel_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_streamer_id'), 'user_streamer', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_streamer_id'), table_name='user_streamer')
    op.drop_table('user_streamer')
    op.drop_index(op.f('ix_vote_id'), table_name='vote')
    op.drop_table('vote')
    op.drop_index(op.f('ix_clip_month_key'), table_name='clip')
    op.drop_index(op.f('ix_clip_id'), table_name='clip')
    op.drop_table('clip')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
