"""Add user_clip_history table for PRO clip history.

Revision ID: user_clip_history_001
Revises: b7f027ceb621
Create Date: 2024-03-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'user_clip_history_001'
down_revision = 'b7f027ceb621'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Note: Initial migration should have created user and related tables
    # This migration adds the user_clip_history table for PRO clip history
    op.create_table(
        'user_clip_history',
        sa.Column('id', sa.String(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('clip_id', sa.String(), nullable=False),
        sa.Column('clip_title', sa.String(), nullable=False),
        sa.Column('clip_url', sa.String(), nullable=False),
        sa.Column('clip_channel', sa.String(), nullable=False),
        sa.Column('thumbnail_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_clip_history_user_id'), 'user_clip_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_clip_history_clip_id'), 'user_clip_history', ['clip_id'], unique=False)
    op.create_index(op.f('ix_user_clip_history_created_at'), 'user_clip_history', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_clip_history_created_at'), table_name='user_clip_history')
    op.drop_index(op.f('ix_user_clip_history_clip_id'), table_name='user_clip_history')
    op.drop_index(op.f('ix_user_clip_history_user_id'), table_name='user_clip_history')
    op.drop_table('user_clip_history')
