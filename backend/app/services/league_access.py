"""One definition of "this user may see this league", used by every router.

Every league-scoped endpoint used to spell the rule out itself as
`League.owner_user_id == current_user.id`. That made the rule impossible to
widen in one place, and it was wrong once a league could have more than one
manager in it. Import `visible_to` instead of writing the comparison.
"""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.league import League
from app.models.league_member import LeagueMember


def visible_to(user_id: int) -> ColumnElement[bool]:
    """A WHERE clause: leagues this user owns, plus leagues they belong to."""
    return or_(
        League.owner_user_id == user_id,
        League.id.in_(
            select(LeagueMember.league_id).where(LeagueMember.user_id == user_id)
        ),
    )


async def ensure_member(
    db: AsyncSession, league_id: int, user_id: int, role: str = "member"
) -> LeagueMember:
    """Idempotently put a user in a league. Does not commit."""
    result = await db.execute(
        select(LeagueMember).where(
            LeagueMember.league_id == league_id, LeagueMember.user_id == user_id
        )
    )
    membership = result.scalar_one_or_none()
    if membership:
        # Owner beats member: connecting again should never demote you.
        if role == "owner" and membership.role != "owner":
            membership.role = "owner"
        return membership

    membership = LeagueMember(league_id=league_id, user_id=user_id, role=role)
    db.add(membership)
    return membership


async def sleeper_id_for(db: AsyncSession, league: League, user_id: int) -> str | None:
    """The Sleeper account to answer *this* manager's questions with.

    `League.sleeper_user_id` belongs to whoever connected the league; for
    anyone else in it, it points at another manager's roster.
    """
    result = await db.execute(
        select(LeagueMember.sleeper_user_id).where(
            LeagueMember.league_id == league.id, LeagueMember.user_id == user_id
        )
    )
    return result.scalar_one_or_none() or league.sleeper_user_id


async def claimed_team_id(db: AsyncSession, league_id: int, user_id: int) -> int | None:
    """Which team this manager runs, by their own claim."""
    result = await db.execute(
        select(LeagueMember.team_id).where(
            LeagueMember.league_id == league_id, LeagueMember.user_id == user_id
        )
    )
    return result.scalar_one_or_none()
