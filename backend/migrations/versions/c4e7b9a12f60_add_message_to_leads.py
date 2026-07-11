"""add message column to leads

Revision ID: c4e7b9a12f60
Revises: f3a9c2b41d7e
Create Date: 2026-07-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4e7b9a12f60'
down_revision = 'f3a9c2b41d7e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('leads', sa.Column('message', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('leads', 'message')
