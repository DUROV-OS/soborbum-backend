"""add ai_chat_attachment file purpose value

Revision ID: 5b3615d19b4e
Revises: 4e740801c6ac
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5b3615d19b4e'
down_revision: Union[str, None] = '4e740801c6ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New FilePurpose.AI_CHAT_ATTACHMENT value, for files employees attach to
    # AI chat messages. Autogenerate doesn't detect added enum values on an
    # existing pg enum type, so this is added by hand (see f030f9e91731 for
    # the same pattern with Module.AI).
    op.execute("ALTER TYPE file_purpose ADD VALUE IF NOT EXISTS 'AI_CHAT_ATTACHMENT'")


def downgrade() -> None:
    # Postgres has no DROP VALUE for enums; the added value is intentionally
    # left in place here.
    pass
