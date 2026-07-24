"""add theme + language preferences to users

Adds users.theme (default 'white') and users.language (default 'en') so a user's
UI preferences persist across devices instead of living only in localStorage.

Revision ID: e1c7a4b9f320
Revises: d7f3a1c8b2e4
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1c7a4b9f320'
down_revision = 'd7f3a1c8b2e4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('theme', sa.String(), nullable=False, server_default='white'))
    op.add_column('users', sa.Column('language', sa.String(length=8), nullable=False, server_default='en'))


def downgrade():
    op.drop_column('users', 'language')
    op.drop_column('users', 'theme')
