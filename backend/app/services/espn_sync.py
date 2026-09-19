"""Refreshing a connected ESPN league from ESPN's API.

The counterpart to `sleeper_sync.refresh_league`, extracted from the sync
endpoint so the same refresh can run from more than one place: pressing "Sync
Data", and a read that finds the league's stored data has aged out.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.league import League
from app.models.team import Team
from app.services.espn_service import ESPNCookies, ESPNService
from app.utils.encryption import ESPNCredentialManager

logger = structlog.get_logger()


def cookies_for(league: League) -> ESPNCookies | None:
    """The league's stored private-league cookies, decrypted."""
    if not (league.espn_s2_encrypted or league.espn_swid_encrypted):
        return None
    return ESPNCookies(
        espn_s2=ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted)
        if league.espn_s2_encrypted else None,
        swid=ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted)
        if league.espn_swid_encrypted else None,
    )


async def refresh_league(
    league: League, db: AsyncSession, *, commit: bool = True
) -> Tuple[List[Dict[str, Any]], int]:
    """Pull the league and its teams up to date. Returns (teams, week)."""
    service = ESPNService()
    cookies = cookies_for(league)

    league_info = await service.get_league_info(str(league.espn_league_id), cookies)

    league.name = league_info["name"]
    # ESPN keeps the same league id across seasons, so a sync has to roll the
    # stored season forward or every downstream fetch stays on last year.
    league.season_year = league_info["season"]
    league.size = league_info["size"]
    league.current_week = league_info["current_week"]
    league.scoring_type = league_info["scoring_type"]
    league.roster_settings = league_info["roster_settings"]
    league.scoring_settings = league_info["scoring_settings"]
    league.last_synced = datetime.now(timezone.utc)

    teams_data = await service.get_teams(str(league.espn_league_id), cookies)

    existing = {
        team.espn_team_id: team
        for team in (
            await db.execute(select(Team).where(Team.league_id == league.id))
        ).scalars().all()
    }

    for team_data in teams_data:
        team = existing.get(team_data["id"])
        if team is None:
            team = Team(espn_team_id=team_data["id"], league_id=league.id)
            db.add(team)

        team.name = team_data["name"]
        team.location = team_data["location"]
        team.nickname = team_data["nickname"]
        team.abbreviation = team_data["abbreviation"]
        team.logo_url = team_data["logo_url"]
        team.wins = team_data["wins"]
        team.losses = team_data["losses"]
        team.ties = team_data["ties"]
        team.points_for = team_data["points_for"]
        team.points_against = team_data["points_against"]

    if commit:
        await db.commit()

    logger.info(
        "ESPN league refreshed",
        league_id=league.id,
        teams=len(teams_data),
        week=league.current_week,
    )
    return teams_data, league.current_week
