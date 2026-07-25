"""add connector_reports (Database Report cache)

Revision ID: f4b8c1d29e70
Revises: e1c7a4b9f320
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa


revision = 'f4b8c1d29e70'
down_revision = 'e1c7a4b9f320'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'connector_reports',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('connector_id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['connector_id'], ['connectors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('connector_id', name='uq_connector_report'),
    )
    op.create_index('ix_connector_reports_connector_id', 'connector_reports', ['connector_id'])


def downgrade():
    op.drop_index('ix_connector_reports_connector_id', table_name='connector_reports')
    op.drop_table('connector_reports')
