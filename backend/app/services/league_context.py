"""
The things every league-scoped endpoint needs: load the league (and prove the
caller belongs to it), decrypt its ESPN cookies, find the caller's team, pull a
roster, and work out who they play this week.

These were copy-pasted into api/news.py and api/assistant.py before a third
consumer made the duplication untenable. Platform differences (ESPN vs Sleeper)
are resolved here once, so routers do not each carry the branch.
"""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.league import League, PlatformType
from app.models.team import Team
from app.models.user import User
from app.services import freshness
from app.services.espn_service import ESPNCookies, ESPNService
from app.services.sleeper_service import SleeperService
from app.utils.encryption import ESPNCredentialManager
from app.services.league_access import claimed_team_id, visible_to

logger = structlog.get_logger()


async def load_league(
    league_id: int, user: User, db: AsyncSession, *, refresh: bool = True
) -> League:
    """The league, if this user owns it or belongs to it. 404 otherwise, never 403.

    A 403 would confirm the league exists, which is more than someone guessing
    ids should learn.

    Loading also brings the league up to date when its stored records, team
    names and current week have aged out — see `services.freshness`. Nobody
    should have to press "Sync Data" to stop being shown last month's
    standings. Pass `refresh=False` where that cost is not worth paying.
    """
    result = await db.execute(
        select(League).where(League.id == league_id, visible_to(user.id))
    )
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found or access denied",
        )
    if refresh:
        await freshness.ensure_fresh(league, db)
    return league


def espn_cookies(league: League) -> Optional[ESPNCookies]:
    s2 = (
        ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted)
        if league.espn_s2_encrypted else None
    )
    swid = (
        ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted)
        if league.espn_swid_encrypted else None
    )
    return ESPNCookies(espn_s2=s2, swid=swid) if (s2 or swid) else None


async def my_team(league: League, user: User, db: AsyncSession) -> Optional[Team]:
    """The caller's own team.

    The claim is per manager (league_members.team_id) so that co-owners of one
    team each keep their own; `Team.owner_user_id` is the fallback for claims
    made before there was such a thing.
    """
    claimed_id = await claimed_team_id(db, league.id, user.id)
    if claimed_id is not None:
        result = await db.execute(select(Team).where(Team.id == claimed_id))
        team = result.scalar_one_or_none()
        if team:
            return team

    result = await db.execute(
        select(Team).where(Team.league_id == league.id, Team.owner_user_id == user.id)
    )
    return result.scalar_one_or_none()


async def all_teams(league: League, db: AsyncSession) -> List[Team]:
    result = await db.execute(select(Team).where(Team.league_id == league.id))
    return list(result.scalars().all())


async def roster_for(league: League, team: Team, week: Optional[int] = None) -> List[dict]:
    """A team's roster in the normalized, ESPN-shaped form the app renders.

    Sleeper's own roster object is arrays of player ids — no names, positions,
    slots or points — so it has to go through `build_team_roster_entries`, the
    same normalizer the teams API uses. Calling Sleeper's raw `get_team_roster`
    here returns an object with no `roster` key at all, which reads as "this
    team has nobody" and silently empties every feature downstream.

    Failing soft is deliberate: one team's roster failing should degrade a page,
    not take the whole request down with it.
    """
    try:
        if league.platform == PlatformType.SLEEPER and league.sleeper_league_id:
            from app.services.sleeper_service import build_team_roster_entries

            return await build_team_roster_entries(
                league.sleeper_league_id,
                team.sleeper_roster_id,
                week=week or league.current_week,
            )
        if league.espn_league_id and team.espn_team_id is not None:
            data = await ESPNService().get_team_roster(
                str(league.espn_league_id),
                team.espn_team_id,
                week=week,
                cookies=espn_cookies(league),
            )
        else:
            return []
        return (data or {}).get("roster", []) or []
    except Exception as e:
        logger.warning("Roster load failed", team=team.name, error=str(e))
        return []


async def opponent_this_week(
    league: League,
    team: Team,
    week: int,
    db: Optional[AsyncSession] = None,
    *,
    teams: Optional[List[Team]] = None,
) -> Optional[Team]:
    """Who this team plays this week.

    The weekly narrative only describes games already played, so it is no use
    before kickoff. The platform's own matchup feed carries the current week's
    pairing, keyed by platform team id, which is then resolved to a team.

    Pass `teams` — the league's teams, already loaded — to resolve that id in
    memory and skip the database entirely. Callers that run several leagues
    concurrently need this: one AsyncSession cannot be used from two coroutines
    at once, and doing so fails the whole request rather than just going slow.
    """
    async def resolve(attribute: str, value) -> Optional[Team]:
        if teams is not None:
            return next((t for t in teams if getattr(t, attribute) == value), None)
        if db is None:
            return None
        return (await db.execute(
            select(Team).where(
                Team.league_id == league.id,
                getattr(Team, attribute) == value,
            )
        )).scalar_one_or_none()

    try:
        if league.platform == PlatformType.SLEEPER and league.sleeper_league_id:
            # Sleeper does not express a matchup as home/away. It returns one
            # row per roster, and two rows sharing a matchup_id are the pairing.
            rows = await SleeperService().get_matchups(league.sleeper_league_id, week)
            mine_row = next(
                (r for r in rows or [] if r.get("roster_id") == team.sleeper_roster_id),
                None,
            )
            if not mine_row or mine_row.get("matchup_id") is None:
                return None  # bye week, or not in this week's slate
            other = next(
                (r for r in rows
                 if r.get("matchup_id") == mine_row["matchup_id"]
                 and r.get("roster_id") != team.sleeper_roster_id),
                None,
            )
            if not other:
                return None
            return await resolve("sleeper_roster_id", other["roster_id"])

        if league.espn_league_id and team.espn_team_id is not None:
            games = await ESPNService().get_matchups(
                str(league.espn_league_id), week=week, cookies=espn_cookies(league)
            )
            mine, home_key, away_key = team.espn_team_id, "home_team_id", "away_team_id"
            attribute = "espn_team_id"
        else:
            return None
    except Exception as e:
        logger.warning("Could not load this week's matchup", error=str(e))
        return None

    for game in games or []:
        home, away = game.get(home_key), game.get(away_key)
        if home is None or away is None:
            continue  # bye week
        other = away if mine == home else home if mine == away else None
        if other is None:
            continue
        return await resolve(attribute, other)
    return None


async def roster_ownership(league: League, db: AsyncSession) -> Dict[str, str]:
    """Every rostered player in the league, mapped to the team that owns him.

    Keys are normalized names so they match the athlete tags ESPN attaches to
    its articles. Per-team failures are swallowed: a partial map still beats no
    map.
    """
    from app.services import news_service  # circular at module scope

    teams = await all_teams(league, db)
    if not teams:
        return {}

    owned: Dict[str, str] = {}

    async def load(team: Team) -> None:
        for player in await roster_for(league, team):
            name = player.get("full_name")
            if name:
                owned[news_service._name_key(name)] = team.name

    await asyncio.gather(*(load(t) for t in teams))
    return owned
