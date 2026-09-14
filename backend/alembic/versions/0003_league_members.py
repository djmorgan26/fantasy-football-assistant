"""league_members: more than one manager per league

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-14

A platform league is one row in `leagues`, and before this it had exactly one
user attached to it, `owner_user_id`. Both connect endpoints reassigned that
column to whoever connected most recently, so the second manager to link the
same ESPN or Sleeper league took it from the first, who then got "League not
found or access denied" everywhere, the board included.

This table is the fix, and it is also what the board needs to work as designed:
the managers of one league have to resolve to one league row to post to one
board.

The backfill puts every current owner in as a member, so the new access check
(`owner OR member`) is a superset of the old one on day one.
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'league_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('league_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='member'),
        sa.Column('sleeper_user_id', sa.String(length=255), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['league_id'], ['leagues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('league_id', 'user_id', name='uq_league_members_league_user'),
    )
    op.create_index(op.f('ix_league_members_id'), 'league_members', ['id'])
    op.create_index(op.f('ix_league_members_league_id'), 'league_members', ['league_id'])
    op.create_index(op.f('ix_league_members_user_id'), 'league_members', ['user_id'])

    op.execute(
        """
        INSERT INTO league_members (league_id, user_id, role, sleeper_user_id)
        SELECT id, owner_user_id, 'owner', sleeper_user_id
        FROM leagues
        WHERE owner_user_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    # Anyone holding a team in a league belongs to it, owner or not, and their
    # existing claim becomes their membership's claim.
    op.execute(
        """
        INSERT INTO league_members (league_id, user_id, role, team_id)
        SELECT league_id, owner_user_id, 'member', id
        FROM teams
        WHERE owner_user_id IS NOT NULL
        ON CONFLICT (league_id, user_id) DO UPDATE SET team_id = EXCLUDED.team_id
        """
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_league_members_user_id'), table_name='league_members')
    op.drop_index(op.f('ix_league_members_league_id'), table_name='league_members')
    op.drop_index(op.f('ix_league_members_id'), table_name='league_members')
    op.drop_table('league_members')
