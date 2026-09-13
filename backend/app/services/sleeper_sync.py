"""
Refreshing a connected Sleeper league from the Sleeper API.

Shared by the connect flow and the sync endpoint so a league is refreshed the
same way whichever way you arrived at it. Before this existed only ESPN leagues
could be re-synced, so a Sleeper league's records, points and current week were
frozen at whatever they were the moment it was connected.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.league import League
from app.models.team import Team
from app.services.sleeper_service import SleeperError, SleeperService

logger = structlog.get_logger()


def scoring_type_from(scoring_settings: Optional[Dict[str, Any]]) -> str:
    """Name the scoring format from the reception value Sleeper reports.

    Sleeper does not label a league "PPR"; it publishes the points awarded per
    reception, and the label is derived from that.
    """
    rec = float((scoring_settings or {}).get("rec") or 0)
    if rec >= 1:
        return "ppr"
    if rec > 0:
        return "half_ppr"
    return "standard"


async def current_week(service: SleeperService, league_data: Dict[str, Any]) -> int:
    """The week this league is on.

    Sleeper's NFL state endpoint is authoritative and shared by every league, so
    it is preferred; the league's own `leg` is the fallback for the offseason
    and for leagues out of step with the NFL calendar.
    """
    leg = int((league_data.get("settings") or {}).get("leg") or 0)
    try:
        state = await service.get_nfl_state()
        week = int(state.get("week") or state.get("display_week") or 0)
        if week:
            return week
    except (SleeperError, ValueError, TypeError) as e:
        logger.warning("Sleeper NFL state unavailable, falling back to league leg", error=str(e))
    return leg or 1


async def refresh_league(
    league: League, db: AsyncSession, *, commit: bool = True
) -> Tuple[int, int]:
    """Pull the league and its teams up to date. Returns (teams, week).

    Records, points-for and points-against all live on the roster objects, so
    one rosters call refreshes every team's standing.
    """
    service = SleeperService()
    sleeper_id = league.sleeper_league_id
    if not sleeper_id:
        raise SleeperError("League has no Sleeper id")

    league_data = await service.get_league(sleeper_id)
    rosters: List[Dict[str, Any]] = await service.get_rosters(sleeper_id)
    users: List[Dict[str, Any]] = await service.get_league_users(sleeper_id)

    league.name = league_data.get("name") or league.name
    league.size = league_data.get("total_rosters") or league.size
    if league_data.get("season"):
        league.season_year = int(league_data["season"])
    league.current_week = await current_week(service, league_data)
    league.scoring_settings = league_data.get("scoring_settings") or {}
    league.scoring_type = scoring_type_from(league.scoring_settings)
    league.roster_settings = {"roster_positions": league_data.get("roster_positions") or []}

    users_by_id = {u.get("user_id"): u for u in users}

    existing = {
        t.sleeper_roster_id: t
        for t in (
            await db.execute(select(Team).where(Team.league_id == league.id))
        ).scalars().all()
    }

    for roster in rosters:
        roster_id = roster.get("roster_id")
        settings = roster.get("settings") or {}
        owner = users_by_id.get(roster.get("owner_id")) or {}

        # Sleeper lets a manager name the team; when they have not, fall back to
        # their display name rather than showing "Team 7".
        name = (
            (roster.get("metadata") or {}).get("team_name")
            or owner.get("display_name")
            or f"Team {roster_id}"
        )
        # Points arrive split into whole and decimal parts.
        points_for = float(settings.get("fpts") or 0) + float(settings.get("fpts_decimal") or 0) / 100
        points_against = (
            float(settings.get("fpts_against") or 0)
            + float(settings.get("fpts_against_decimal") or 0) / 100
        )

        team = existing.get(roster_id)
        if team is None:
            team = Team(league_id=league.id, sleeper_roster_id=roster_id)
            db.add(team)

        team.sleeper_owner_id = roster.get("owner_id")
        team.name = name
        team.abbreviation = (owner.get("display_name") or name)[:10]
        team.logo_url = (
            f"https://sleepercdn.com/avatars/thumbs/{owner['avatar']}"
            if owner.get("avatar") else None
        )
        team.wins = settings.get("wins", 0)
        team.losses = settings.get("losses", 0)
        team.ties = settings.get("ties", 0)
        team.points_for = points_for
        team.points_against = points_against

    if commit:
        await db.commit()

    logger.info(
        "Sleeper league refreshed",
        league_id=league.id,
        teams=len(rosters),
        week=league.current_week,
    )
    return len(rosters), league.current_week


async def normalized_matchups(
    sleeper_league_id: str, week: int
) -> List[Dict[str, Any]]:
    """Sleeper's matchup rows, paired into the home/away shape ESPN produces.

    Sleeper returns one row per roster and expresses the pairing by a shared
    `matchup_id`; there is no notion of home and away. The lower roster id is
    treated as home so the ordering is at least stable between calls.

    Sleeper publishes no per-matchup projection, so that stays None rather than
    being invented — the UI already renders "No projection".
    """
    service = SleeperService()
    rows = await service.get_matchups(sleeper_league_id, week)

    by_matchup: Dict[Any, List[Dict[str, Any]]] = {}
    for row in rows or []:
        matchup_id = row.get("matchup_id")
        if matchup_id is None:
            continue  # a roster on bye is in no pairing
        by_matchup.setdefault(matchup_id, []).append(row)

    out = []
    for matchup_id, pair in sorted(by_matchup.items(), key=lambda kv: (kv[0] is None, kv[0])):
        pair.sort(key=lambda r: r.get("roster_id") or 0)
        home = pair[0]
        away = pair[1] if len(pair) > 1 else None

        home_score = float(home.get("points") or 0)
        away_score = float(away.get("points") or 0) if away else 0.0

        if not away:
            winner = "UNDECIDED"
        elif home_score == away_score:
            # Both still on zero means nobody has kicked off, not a tie.
            winner = "UNDECIDED" if home_score == 0 else "TIE"
        else:
            winner = "HOME" if home_score > away_score else "AWAY"

        out.append({
            "matchup_id": matchup_id,
            "week": week,
            "home_team_id": home.get("roster_id"),
            "away_team_id": away.get("roster_id") if away else None,
            "home_score": home_score,
            "away_score": away_score,
            "home_projected_score": None,
            "away_projected_score": None,
            "is_playoff": False,
            "winner": winner,
        })
    return out
