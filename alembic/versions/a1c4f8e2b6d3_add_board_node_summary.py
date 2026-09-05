"""add board_nodes.summary

Revision ID: a1c4f8e2b6d3
Revises: 3f7a9c2e5d10
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1c4f8e2b6d3'
down_revision: Union[str, None] = '3f7a9c2e5d10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Node descriptions are now written to be substantial (500+ words) so the
    # council/conductor have a real document to work with - summary holds the
    # short, 2-3 paragraph AI condensation served to the frontend instead of
    # the full text. Nullable: existing nodes get one lazily on their next
    # AI-driven edit.
    op.add_column('board_nodes', sa.Column('summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('board_nodes', 'summary')
