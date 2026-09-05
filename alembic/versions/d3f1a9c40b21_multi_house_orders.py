"""multi-house orders: order_type + houses_count on clients, several productions per cycle

Revision ID: d3f1a9c40b21
Revises: b2e5c9d17a34
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd3f1a9c40b21'
down_revision: Union[str, None] = 'b2e5c9d17a34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # One клиент can now carry several дома в производстве. The order kind is
    # chosen at «обсуждение» (order_type), the house count at «согласование»
    # (houses_count), and on POSTPAYMENT one productions row is spun up per дом.
    order_type = sa.Enum('SINGLE', 'MULTIPLE', name='order_type')
    order_type.create(op.get_bind(), checkfirst=True)

    op.add_column('clients', sa.Column('order_type', order_type, nullable=True))
    op.add_column(
        'clients',
        sa.Column('houses_count', sa.Integer(), nullable=False, server_default='1'),
    )

    op.add_column(
        'productions',
        sa.Column('house_index', sa.Integer(), nullable=False, server_default='1'),
    )
    op.add_column(
        'productions',
        sa.Column('name', sa.String(length=255), nullable=False, server_default='Дом'),
    )
    # A цикл may now own more than one production project.
    op.drop_constraint('productions_cycle_id_key', 'productions', type_='unique')


def downgrade() -> None:
    op.create_unique_constraint('productions_cycle_id_key', 'productions', ['cycle_id'])
    op.drop_column('productions', 'name')
    op.drop_column('productions', 'house_index')
    op.drop_column('clients', 'houses_count')
    op.drop_column('clients', 'order_type')
    sa.Enum(name='order_type').drop(op.get_bind(), checkfirst=True)
