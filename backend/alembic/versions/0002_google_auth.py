"""Google sign-in: link column, nullable password, case-insensitive email

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-14

Three changes, each of which has to hold on a database that already contains
real accounts:

- users.google_sub, the Google subject id we link on. Unique so one Google
  account cannot be attached to two of ours, nullable so every existing
  password account stays valid.
- users.hashed_password becomes nullable, for accounts created through Google
  that never had a password.
- a unique index on lower(email). The application normalizes addresses now,
  but the plain unique index on `email` would still happily accept
  "Dave@x.com" alongside "dave@x.com", and those two rows would then fight
  over one Google account. This makes that impossible at the database rather
  than trusting every future code path to remember.
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('google_sub', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.Text(), nullable=True))
    op.create_index(op.f('ix_users_google_sub'), 'users', ['google_sub'], unique=True)
    op.alter_column('users', 'hashed_password', existing_type=sa.String(length=255), nullable=True)
    op.create_index(
        'ix_users_email_lower',
        'users',
        [sa.text('lower(email)')],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_users_email_lower', table_name='users')
    # Only safe if no passwordless accounts exist; a Google-only user has
    # nothing to put here and the column cannot go back to NOT NULL.
    op.alter_column('users', 'hashed_password', existing_type=sa.String(length=255), nullable=False)
    op.drop_index(op.f('ix_users_google_sub'), table_name='users')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'google_sub')
