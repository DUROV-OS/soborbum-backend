"""add ai_cache_entries table

Revision ID: c7d29a4f16e8
Revises: a1c4f8e2b6d3
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c7d29a4f16e8'
down_revision: Union[str, None] = 'a1c4f8e2b6d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Generic TTL cache for AI-generated answers that aren't a chat turn -
    # section analytics and task priorities (see app/ai/cache.py).
    op.create_table(
        'ai_cache_entries',
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade() -> None:
    op.drop_table('ai_cache_entries')
