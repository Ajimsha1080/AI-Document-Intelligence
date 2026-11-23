"""add tenant webhook_url column

Revision ID: 801025555e40
Revises: 701025555e39
Create Date: 2026-11-23 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '801025555e40'
down_revision: Union[str, Sequence[str], None] = '701025555e39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tenants', schema=None) as batch_op:
        batch_op.add_column(sa.Column('webhook_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('tenants', schema=None) as batch_op:
        batch_op.drop_column('webhook_url')
