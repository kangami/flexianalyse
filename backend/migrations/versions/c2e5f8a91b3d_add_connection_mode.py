"""add connection_mode to connectors

'cloud' (default) or 'local' (on-prem dial-home agent). Local connectors hold
their DB credentials on the agent, not in the cloud.

Revision ID: c2e5f8a91b3d
Revises: a1d4c8e93f2b
Create Date: 2026-07-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c2e5f8a91b3d'
down_revision = 'a1d4c8e93f2b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('connectors', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('connection_mode', sa.String(), nullable=False, server_default='cloud')
        )


def downgrade():
    with op.batch_alter_table('connectors', schema=None) as batch_op:
        batch_op.drop_column('connection_mode')
