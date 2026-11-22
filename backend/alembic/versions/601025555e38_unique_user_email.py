"""make email globally unique

Revision ID: 601025555e38
Revises: 401025555e37
Create Date: 2026-11-22 01:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '601025555e38'
down_revision: Union[str, Sequence[str], None] = '401025555e37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        try:
            batch_op.drop_index('ix_users_email')
        except Exception:
            pass
        batch_op.create_index('ix_users_email_unique', ['email'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_email_unique')
        batch_op.create_index('ix_users_email', ['email'], unique=False)
