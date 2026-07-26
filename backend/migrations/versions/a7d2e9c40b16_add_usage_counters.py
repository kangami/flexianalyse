"""add usage_counters (fair-use monthly question cap)

Revision ID: a7d2e9c40b16
Revises: b2c9d4e17f38
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7d2e9c40b16'
down_revision = 'b2c9d4e17f38'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'usage_counters',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('period', sa.String(), nullable=False),
        sa.Column('questions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'period', name='uq_usage_org_period'),
    )
    op.create_index('ix_usage_counters_organization_id', 'usage_counters', ['organization_id'])


def downgrade():
    op.drop_index('ix_usage_counters_organization_id', table_name='usage_counters')
    op.drop_table('usage_counters')
