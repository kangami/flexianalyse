"""add firebase_uid to users

Firebase devient la source de vérité de l'identité (Google + email/mot de passe).
`firebase_uid` rattache la ligne users au compte Firebase ; il est nullable pour
les comptes créés avant la bascule, et unique pour qu'un uid ne puisse pas être
réclamé deux fois.

Revision ID: d5c81e0a9f14
Revises: c4e7b9a12f60
Create Date: 2026-07-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5c81e0a9f14'
down_revision = 'c4e7b9a12f60'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('firebase_uid', sa.String(), nullable=True))
        batch_op.create_unique_constraint('uq_users_firebase_uid', ['firebase_uid'])
        batch_op.create_index('ix_users_firebase_uid', ['firebase_uid'], unique=False)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_firebase_uid')
        batch_op.drop_constraint('uq_users_firebase_uid', type_='unique')
        batch_op.drop_column('firebase_uid')
