"""restructure warehouse material fields

Revision ID: 4e740801c6ac
Revises: 769a8c5298d4
Create Date: 2026-09-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4e740801c6ac'
down_revision: Union[str, None] = '769a8c5298d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

WAREHOUSE_VALUES = ['Склад Технология', 'Склад ИД Групп']
CATEGORY_VALUES = [
    'без категории', 'брусы/доска', 'вентиляция', 'вода/канализация', 'инструмент',
    'комплекты для сборки', 'краска/лак/масло', 'кровельный материал', 'мебель', 'мембрана',
    'метизы', 'окна и двери', 'печное', 'расходные материалы', 'сваи',
    'утепление и изоляции', 'хоз.блок', 'чаны', 'электрика',
]

warehouse_enum = postgresql.ENUM(*WAREHOUSE_VALUES, name='warehouse_name')
category_enum = postgresql.ENUM(*CATEGORY_VALUES, name='material_category')


def upgrade() -> None:
    bind = op.get_bind()
    warehouse_enum.create(bind, checkfirst=True)
    category_enum.create(bind, checkfirst=True)

    op.add_column(
        'warehouse_materials',
        sa.Column('warehouse', warehouse_enum, nullable=False, server_default='Склад Технология'),
    )
    op.add_column(
        'warehouse_materials',
        sa.Column('category', category_enum, nullable=False, server_default='без категории'),
    )
    op.add_column('warehouse_materials', sa.Column('code', sa.String(length=64), nullable=True))
    op.execute("UPDATE warehouse_materials SET code = 'M' || id WHERE code IS NULL")
    op.alter_column('warehouse_materials', 'code', nullable=False)
    op.add_column(
        'warehouse_materials',
        sa.Column('is_fractional', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'warehouse_materials',
        sa.Column('purchase_price', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0'),
    )

    # server defaults above only exist to backfill pre-existing rows; the ORM
    # model doesn't declare them, so drop them to keep the schema in sync
    op.alter_column('warehouse_materials', 'warehouse', server_default=None)
    op.alter_column('warehouse_materials', 'category', server_default=None)
    op.alter_column('warehouse_materials', 'is_fractional', server_default=None)
    op.alter_column('warehouse_materials', 'purchase_price', server_default=None)

    op.create_unique_constraint(
        'uq_warehouse_materials_warehouse_code', 'warehouse_materials', ['warehouse', 'code']
    )

    op.drop_column('warehouse_materials', 'material_type')
    op.drop_column('warehouse_materials', 'size')
    op.drop_column('warehouse_materials', 'supplier_name')
    op.drop_column('warehouse_materials', 'supplier_contact')
    op.drop_column('warehouse_materials', 'supplier_phone')


def downgrade() -> None:
    op.add_column(
        'warehouse_materials', sa.Column('material_type', sa.String(length=255), nullable=False, server_default='')
    )
    op.add_column('warehouse_materials', sa.Column('size', sa.String(length=255), nullable=True))
    op.add_column('warehouse_materials', sa.Column('supplier_name', sa.String(length=255), nullable=True))
    op.add_column('warehouse_materials', sa.Column('supplier_contact', sa.String(length=255), nullable=True))
    op.add_column('warehouse_materials', sa.Column('supplier_phone', sa.String(length=64), nullable=True))
    op.alter_column('warehouse_materials', 'material_type', server_default=None)

    op.drop_constraint('uq_warehouse_materials_warehouse_code', 'warehouse_materials', type_='unique')
    op.drop_column('warehouse_materials', 'purchase_price')
    op.drop_column('warehouse_materials', 'is_fractional')
    op.drop_column('warehouse_materials', 'code')
    op.drop_column('warehouse_materials', 'category')
    op.drop_column('warehouse_materials', 'warehouse')

    bind = op.get_bind()
    category_enum.drop(bind, checkfirst=True)
    warehouse_enum.drop(bind, checkfirst=True)
