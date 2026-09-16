"""Store an optional Sleeper bearer token per league, encrypted.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-16

Sleeper's public v1 API only ever returns *completed* transactions, so a trade
offer awaiting your answer is invisible to it. Pending offers come from
sleeper.com/graphql, which needs the manager's own token. Stored Fernet-encrypted
through the same `app.utils.encryption` path as the ESPN cookies alongside it,
and entirely optional: a league without one falls back to trade history.
"""
from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leagues", sa.Column("sleeper_token_encrypted", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("leagues", "sleeper_token_encrypted")
