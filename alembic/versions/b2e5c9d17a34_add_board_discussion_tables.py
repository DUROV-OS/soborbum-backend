"""add board discussion tables

Revision ID: b2e5c9d17a34
Revises: c7d29a4f16e8
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2e5c9d17a34'
down_revision: Union[str, None] = 'c7d29a4f16e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Free-form chat with the "Совет директоров" (app.board.discussion) - a
    # plain thread that never edits the tree, unlike board_proposals.
    # discussions.node_id is ON DELETE SET NULL on purpose: a structural edit
    # that removes the node leaves the thread and its history intact.
    op.create_table(
        'board_discussions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['node_id'], ['board_nodes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'board_discussion_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('discussion_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('council', sa.JSON(), nullable=True),
        sa.Column('research_brief', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['discussion_id'], ['board_discussions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_board_discussion_messages_discussion_id', 'board_discussion_messages', ['discussion_id'])
    op.create_index('ix_board_discussions_node_id', 'board_discussions', ['node_id'])


def downgrade() -> None:
    op.drop_index('ix_board_discussions_node_id', table_name='board_discussions')
    op.drop_index('ix_board_discussion_messages_discussion_id', table_name='board_discussion_messages')
    op.drop_table('board_discussion_messages')
    op.drop_table('board_discussions')
