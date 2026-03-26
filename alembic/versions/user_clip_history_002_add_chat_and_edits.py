"""Add chat and edit history to user_clip_history table

Revision ID: user_clip_history_002
Revises: user_clip_history_001
Create Date: 2026-03-26 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'user_clip_history_002'
down_revision = 'user_clip_history_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns for storing edits, chat, and timeline
    op.add_column('user_clip_history', sa.Column('clip_description', sa.String(), nullable=True))
    op.add_column('user_clip_history', sa.Column('clip_tags', sa.Text(), nullable=True))
    op.add_column('user_clip_history', sa.Column('edited_title', sa.String(), nullable=True))
    op.add_column('user_clip_history', sa.Column('chat_messages', sa.Text(), nullable=True))
    op.add_column('user_clip_history', sa.Column('edit_history', sa.Text(), nullable=True))
    op.add_column('user_clip_history', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('user_clip_history', sa.Column('last_edited_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_clip_history', 'last_edited_at')
    op.drop_column('user_clip_history', 'updated_at')
    op.drop_column('user_clip_history', 'edit_history')
    op.drop_column('user_clip_history', 'chat_messages')
    op.drop_column('user_clip_history', 'edited_title')
    op.drop_column('user_clip_history', 'clip_tags')
    op.drop_column('user_clip_history', 'clip_description')
