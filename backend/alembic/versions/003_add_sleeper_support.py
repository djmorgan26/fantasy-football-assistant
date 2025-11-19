"""Add Sleeper platform support

Revision ID: 003
Revises: 002
Create Date: 2025-01-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add platform enum type
    op.execute("CREATE TYPE platformtype AS ENUM ('espn', 'sleeper')")

    # Add platform column to leagues table
    op.add_column('leagues', sa.Column('platform', sa.Enum('espn', 'sleeper', name='platformtype'),
                                       nullable=False, server_default='espn'))

    # Make espn_league_id nullable (was NOT NULL before)
    op.alter_column('leagues', 'espn_league_id',
                   existing_type=sa.INTEGER(),
                   nullable=True)

    # Add Sleeper-specific columns to leagues
    op.add_column('leagues', sa.Column('sleeper_league_id', sa.String(255), nullable=True))
    op.add_column('leagues', sa.Column('sleeper_user_id', sa.String(255), nullable=True))

    # Create indexes for Sleeper league IDs
    op.create_index('ix_leagues_sleeper_league_id', 'leagues', ['sleeper_league_id'])
    op.create_index('ix_leagues_platform', 'leagues', ['platform'])

    # Make espn_team_id nullable in teams table
    op.alter_column('teams', 'espn_team_id',
                   existing_type=sa.INTEGER(),
                   nullable=True)

    # Add Sleeper-specific columns to teams
    op.add_column('teams', sa.Column('sleeper_roster_id', sa.INTEGER(), nullable=True))
    op.add_column('teams', sa.Column('sleeper_owner_id', sa.String(255), nullable=True))


def downgrade() -> None:
    # Remove Sleeper-specific columns from teams
    op.drop_column('teams', 'sleeper_owner_id')
    op.drop_column('teams', 'sleeper_roster_id')

    # Make espn_team_id NOT NULL again
    op.alter_column('teams', 'espn_team_id',
                   existing_type=sa.INTEGER(),
                   nullable=False)

    # Remove indexes
    op.drop_index('ix_leagues_platform', 'leagues')
    op.drop_index('ix_leagues_sleeper_league_id', 'leagues')

    # Remove Sleeper-specific columns from leagues
    op.drop_column('leagues', 'sleeper_user_id')
    op.drop_column('leagues', 'sleeper_league_id')

    # Make espn_league_id NOT NULL again
    op.alter_column('leagues', 'espn_league_id',
                   existing_type=sa.INTEGER(),
                   nullable=False)

    # Remove platform column
    op.drop_column('leagues', 'platform')

    # Drop platform enum type
    op.execute("DROP TYPE platformtype")
