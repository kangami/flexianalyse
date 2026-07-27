"""add Stripe billing fields to organizations

Revision ID: c3f8a1b6d29e
Revises: a7d2e9c40b16
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3f8a1b6d29e'
down_revision = 'a7d2e9c40b16'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('organizations', sa.Column('stripe_customer_id', sa.String(), nullable=True))
    op.add_column('organizations', sa.Column('stripe_subscription_id', sa.String(), nullable=True))
    op.add_column('organizations', sa.Column('plan_status', sa.String(), nullable=True))


def downgrade():
    op.drop_column('organizations', 'plan_status')
    op.drop_column('organizations', 'stripe_subscription_id')
    op.drop_column('organizations', 'stripe_customer_id')
