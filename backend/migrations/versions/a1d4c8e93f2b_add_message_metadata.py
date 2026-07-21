"""add message_metadata to messages

Stocke le payload structuré d'un tour assistant (SQL généré, colonnes, lignes,
sources) pour restaurer la grille de résultats à la réouverture d'une conversation.

Revision ID: a1d4c8e93f2b
Revises: f7c1a9e2b4d0
Create Date: 2026-07-20 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1d4c8e93f2b'
down_revision = 'f7c1a9e2b4d0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('message_metadata', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_column('message_metadata')
