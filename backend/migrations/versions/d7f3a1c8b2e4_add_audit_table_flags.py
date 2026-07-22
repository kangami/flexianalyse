"""add audit-table flags

Adds:
- connectors.hide_audit_tables : per-connector toggle (default True) to exclude
  detected audit/log/system tables from the ER diagram and Text-to-SQL retrieval.
- connector_schema_tables.is_audit : per-table flag set at crawl time by the name
  heuristic, so the diagram and retrieval can filter consistently without
  re-running the heuristic everywhere.

Revision ID: d7f3a1c8b2e4
Revises: c2e5f8a91b3d
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7f3a1c8b2e4'
down_revision = 'c2e5f8a91b3d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('connectors', sa.Column(
        'hide_audit_tables', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('connector_schema_tables', sa.Column(
        'is_audit', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column('connector_schema_tables', 'is_audit')
    op.drop_column('connectors', 'hide_audit_tables')
