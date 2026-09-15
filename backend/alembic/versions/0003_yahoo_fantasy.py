"""Add Yahoo Fantasy account and league identifiers.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-15
"""
from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL persists SQLAlchemy enums separately from the table. SQLite's
    # enum is a CHECK-less VARCHAR, so it needs no corresponding operation.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE platformtype ADD VALUE IF NOT EXISTS 'YAHOO'")
    op.add_column("users", sa.Column("yahoo_access_token_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("yahoo_refresh_token_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("yahoo_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("yahoo_guid", sa.String(length=255), nullable=True))
    op.add_column("leagues", sa.Column("yahoo_league_key", sa.String(length=255), nullable=True))
    op.add_column("leagues", sa.Column("yahoo_user_guid", sa.String(length=255), nullable=True))
    op.create_index("ix_leagues_yahoo_league_key", "leagues", ["yahoo_league_key"])
    op.add_column("teams", sa.Column("yahoo_team_key", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("teams", "yahoo_team_key")
    op.drop_index("ix_leagues_yahoo_league_key", table_name="leagues")
    op.drop_column("leagues", "yahoo_user_guid")
    op.drop_column("leagues", "yahoo_league_key")
    op.drop_column("users", "yahoo_guid")
    op.drop_column("users", "yahoo_token_expires_at")
    op.drop_column("users", "yahoo_refresh_token_encrypted")
    op.drop_column("users", "yahoo_access_token_encrypted")
