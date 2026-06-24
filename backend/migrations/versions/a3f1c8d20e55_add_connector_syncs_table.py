"""add connector_syncs table

Revision ID: a3f1c8d20e55
Revises: 9139bf022744
Create Date: 2026-06-23 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3f1c8d20e55'
down_revision = '9139bf022744'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'connector_syncs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('connector_id', sa.Uuid(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='running'),
        sa.Column('resources_processed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('resources_created', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('resources_updated', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('resources_deleted', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('total_batches', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('batches_completed', sa.Integer(), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['connector_id'], ['connectors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_connector_syncs_connector_id', 'connector_syncs', ['connector_id'])


def downgrade():
    op.drop_index('ix_connector_syncs_connector_id', table_name='connector_syncs')
    op.drop_table('connector_syncs')
