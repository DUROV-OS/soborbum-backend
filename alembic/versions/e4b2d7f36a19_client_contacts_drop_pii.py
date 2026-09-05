"""client contacts array instead of inn/passport/birth_date

Revision ID: e4b2d7f36a19
Revises: d3f1a9c40b21
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e4b2d7f36a19'
down_revision: Union[str, None] = 'd3f1a9c40b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Паспорт, ИНН и дата рождения для работы с клиентом не нужны — вместо них
    # держим список способов связи [{"messenger": ..., "contact": ...}].
    op.add_column(
        'clients',
        sa.Column('contacts', sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    # Существующим клиентам — telegram на их номер телефона.
    op.execute(
        """
        UPDATE clients
        SET contacts = json_build_array(
            json_build_object('messenger', 'telegram', 'contact', phone)
        )
        WHERE phone IS NOT NULL AND phone <> ''
        """
    )
    op.alter_column('clients', 'contacts', server_default=None)

    op.drop_column('clients', 'birth_date')
    op.drop_column('clients', 'passport_number')
    op.drop_column('clients', 'inn')


def downgrade() -> None:
    op.add_column(
        'clients',
        sa.Column('inn', sa.String(length=32), nullable=False, server_default=''),
    )
    op.add_column(
        'clients',
        sa.Column('passport_number', sa.String(length=64), nullable=False, server_default=''),
    )
    op.add_column(
        'clients',
        sa.Column('birth_date', sa.Date(), nullable=False, server_default=sa.text("'1970-01-01'")),
    )
    op.alter_column('clients', 'inn', server_default=None)
    op.alter_column('clients', 'passport_number', server_default=None)
    op.alter_column('clients', 'birth_date', server_default=None)

    op.drop_column('clients', 'contacts')
