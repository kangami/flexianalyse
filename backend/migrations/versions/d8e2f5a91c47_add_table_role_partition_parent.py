"""add semantic role + partition parent to the schema catalog

connector_schema_tables.table_role (business | partition_child | audit | junction)
and partition_parent, set at crawl time, so the agent understands the database
layout (partitioned tables, audit copies) instead of treating every table alike.

Revision ID: d8e2f5a91c47
Revises: c3f8a1b6d29e
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa


revision = 'd8e2f5a91c47'
down_revision = 'c3f8a1b6d29e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('connector_schema_tables', sa.Column(
        'table_role', sa.String(), nullable=False, server_default='business'))
    op.add_column('connector_schema_tables', sa.Column(
        'partition_parent', sa.String(), nullable=True))


def downgrade():
    op.drop_column('connector_schema_tables', 'partition_parent')
    op.drop_column('connector_schema_tables', 'table_role')
