"""add board module and tables

Revision ID: 3f7a9c2e5d10
Revises: 5b3615d19b4e
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f7a9c2e5d10'
down_revision: Union[str, None] = '5b3615d19b4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New Module.BOARD access-grant value. Autogenerate doesn't detect added
    # enum values on an existing pg enum type, so this is added by hand (see
    # f030f9e91731 for the same treatment of Module.AI).
    op.execute("ALTER TYPE module ADD VALUE IF NOT EXISTS 'BOARD'")

    op.create_table('board_nodes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('color', sa.Enum('GREEN', 'YELLOW', 'RED', name='board_node_color'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['board_nodes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('board_proposals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('node_id', sa.Integer(), nullable=False),
    sa.Column('requested_by_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'APPLIED', 'CANCELLED', name='board_proposal_status'), nullable=False),
    sa.Column('rounds', sa.JSON(), nullable=False),
    sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['node_id'], ['board_nodes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('board_node_changes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('node_id', sa.Integer(), nullable=False),
    sa.Column('proposal_id', sa.Integer(), nullable=True),
    sa.Column('source', sa.Enum('COUNCIL', 'ACTUALIZE', 'MANUAL', name='board_change_source'), nullable=False),
    sa.Column('change_type', sa.Enum('CREATED', 'UPDATED', 'DELETED', name='board_change_type'), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('old_description', sa.Text(), nullable=True),
    sa.Column('new_description', sa.Text(), nullable=True),
    sa.Column('old_color', sa.String(length=16), nullable=True),
    sa.Column('new_color', sa.String(length=16), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['proposal_id'], ['board_proposals.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('board_node_changes')
    op.drop_table('board_proposals')
    op.drop_table('board_nodes')
    # Note: Postgres has no DROP VALUE for enums, so the 'BOARD' value added
    # to the `module` type in upgrade() is intentionally left in place here.
