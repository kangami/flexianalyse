"""add engine to connectors

Moteur SQL précis (postgresql, mysql, mariadb, oracle, mssql) porté par un
connecteur de type 'sql'. Nullable : les connecteurs existants (et non-SQL)
restent sans engine.

Revision ID: e6b2f1a4c908
Revises: d5c81e0a9f14
Create Date: 2026-07-18 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6b2f1a4c908'
down_revision = 'd5c81e0a9f14'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('connectors', schema=None) as batch_op:
        batch_op.add_column(sa.Column('engine', sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table('connectors', schema=None) as batch_op:
        batch_op.drop_column('engine')
