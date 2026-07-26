"""add schema crawl progress counters to connectors

Adds connectors.schema_crawl_done / schema_crawl_total so the crawl can report
per-batch progress (embedding batches) and the UI ring fills accordingly.

Revision ID: b2c9d4e17f38
Revises: f4b8c1d29e70
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c9d4e17f38'
down_revision = 'f4b8c1d29e70'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('connectors', sa.Column('schema_crawl_done', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('connectors', sa.Column('schema_crawl_total', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('connectors', 'schema_crawl_total')
    op.drop_column('connectors', 'schema_crawl_done')
