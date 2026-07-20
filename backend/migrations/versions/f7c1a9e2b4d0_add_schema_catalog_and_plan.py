"""add schema catalog + org plan + connector crawl status

Catalogue de schéma persistant par connecteur SQL (une ligne par table, avec
embedding pour le retrieval de tables), palier `plan` sur l'organisation, et
état du crawl sur le connecteur.

Revision ID: f7c1a9e2b4d0
Revises: e6b2f1a4c908
Create Date: 2026-07-20 19:30:00.000000

"""
import os
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = 'f7c1a9e2b4d0'
down_revision = 'e6b2f1a4c908'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'connector_schema_tables',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('connector_id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('table_name', sa.String(), nullable=False),
        sa.Column('columns', sa.JSON(), nullable=True),
        sa.Column('primary_keys', sa.JSON(), nullable=True),
        sa.Column('foreign_keys', sa.JSON(), nullable=True),
        sa.Column('row_estimate', sa.BigInteger(), nullable=True),
        sa.Column('embedding', Vector(int(os.getenv('EMBEDDING_DIMENSIONS', '1536'))), nullable=True),
        sa.Column('introspected_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['connector_id'], ['connectors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('connector_id', 'table_name', name='uq_connector_table'),
    )
    op.create_index(
        op.f('ix_connector_schema_tables_connector_id'),
        'connector_schema_tables', ['connector_id'], unique=False,
    )

    with op.batch_alter_table('organizations', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('plan', sa.String(), nullable=False, server_default='free')
        )

    with op.batch_alter_table('connectors', schema=None) as batch_op:
        batch_op.add_column(sa.Column('schema_crawl_status', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('schema_crawled_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('schema_table_count', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('connectors', schema=None) as batch_op:
        batch_op.drop_column('schema_table_count')
        batch_op.drop_column('schema_crawled_at')
        batch_op.drop_column('schema_crawl_status')

    with op.batch_alter_table('organizations', schema=None) as batch_op:
        batch_op.drop_column('plan')

    op.drop_index(
        op.f('ix_connector_schema_tables_connector_id'),
        table_name='connector_schema_tables',
    )
    op.drop_table('connector_schema_tables')
