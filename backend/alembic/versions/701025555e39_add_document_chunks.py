"""add document_chunks table

Revision ID: 701025555e39
Revises: 601025555e38
Create Date: 2026-11-22 02:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '701025555e39'
down_revision: Union[str, Sequence[str], None] = '601025555e38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('chunk_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_text_normalized', sa.Text(), nullable=False),
        sa.Column('bounding_box', sa.JSON(), nullable=True),
        sa.Column('embedding', sa.JSON(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('document_chunks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_document_chunks_document_id'), ['document_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_document_chunks_tenant_id'), ['tenant_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('document_chunks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_document_chunks_tenant_id'))
        batch_op.drop_index(batch_op.f('ix_document_chunks_document_id'))
    op.drop_table('document_chunks')
