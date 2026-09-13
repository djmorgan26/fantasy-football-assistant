"""
Everything you own, across every league, in one place.

Playing in more than one league creates a situation no single-league view can
show you: the same player is on your roster in one league and on the roster of
the person you are playing in another. Every touchdown he scores helps you and
hurts you at the same time, and most people do not notice until they are
watching a game with no idea who to root for.

That conflict is the headline here. Underneath it sit the two other things a
single-league view cannot answer — how exposed you are to one player across all
your teams, and which of your weeks are actually in trouble.

Players are matched across leagues **by normalized name**, not by id: ESPN and
Sleeper number the same human differently, so an id-based join would find
nothing between an ESPN league and a Sleeper one, which is exactly the case
this page exists for.
"""
import asyncio
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.db.database import get_database
from app.models.league import League
from app.models.team import Team
from app.models.user import User
from app.services import league_context, news_service

logger = structlog.get_logger()
router = APIRouter(prefix="/portfolio", tags=["portfolio"])

UNAVAILABLE = {"OUT", "INJURY_RESERVE", "IR", "SUSPENSION"}
DOUBTFUL = {"DOUBTFUL", "QUESTIONABLE"}


def verdict(for_count: int, against_count: int) -> str:
    """How to feel about a player you are both rooting for and against.

    Only starters count on either side — a player on somebody's bench is not
    doing anything to anybody.
    """
    if for_count and not against_count:
        return "rooting for him"
    if against_count and not for_count:
        return "rooting against him"
    if for_count == against_count:
        return "a genuine wash"
    if for_count > against_count:
        return "net rooting for him"
    return "net rooting against him"


def _entry(league: League, team: Team, player: dict) -> dict:
    return {
        "league_id": league.id,
        "league": league.name,
        "team": team.name,
        "starting": bool(player.get("is_starter")),
        "slot": player.get("lineup_slot_name"),
        "projected": round(player.get("projected_points") or 0, 1),
        "points": round(player.get("applied_points") or 0, 1),
    }


async def _league_slice(
    league: League, user: User, db: AsyncSession
) -> Optional[Dict[str, Any]]:
    """One league's worth of context: my team, my opponent, and both rosters."""
    team = await league_context.my_team(league, user, db)
    if not team:
        return None

    week = league.current_week or 1
    opponent = await league_context.opponent_this_week(league, team, week, db)

    mine, theirs = await asyncio.gather(
        league_context.roster_for(league, team),
        league_context.roster_for(league, opponent) if opponent else _empty(),
    )

    return {
        "league": league,
        "team": team,
        "opponent": opponent,
        "week": week,
        "mine": mine,
        "theirs": theirs,
    }


async def _empty() -> List[dict]:
    return []


@router.get("")
@router.get("/")
async def portfolio(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    leagues = (
        await db.execute(
            select(League)
            .where(League.owner_user_id == current_user.id)
            .order_by(League.name)
        )
    ).scalars().all()

    slices = await asyncio.gather(
        *(_league_slice(league, current_user, db) for league in leagues)
    )

    # Leagues with no claimed team cannot contribute, and the UI should say why
    # rather than silently showing fewer leagues than the user has.
    unclaimed = [
        {"league_id": league.id, "name": league.name}
        for league, data in zip(leagues, slices) if data is None
    ]
    active = [s for s in slices if s]

    # ---- per-league week summary -------------------------------------------
    weeks = []
    for s in active:
        mine_starters = [p for p in s["mine"] if p.get("is_starter")]
        their_starters = [p for p in s["theirs"] if p.get("is_starter")]

        my_points = round(sum(p.get("applied_points") or 0 for p in mine_starters), 1)
        their_points = round(sum(p.get("applied_points") or 0 for p in their_starters), 1)
        my_proj = round(sum(p.get("projected_points") or 0 for p in mine_starters), 1)
        their_proj = round(sum(p.get("projected_points") or 0 for p in their_starters), 1)

        hurt = [
            {
                "player": p.get("full_name"),
                "slot": p.get("lineup_slot_name"),
                "status": p.get("injury_status"),
            }
            for p in mine_starters
            if p.get("injury_status") in (UNAVAILABLE | DOUBTFUL)
        ]

        margin = round(my_proj - their_proj, 1)
        weeks.append({
            "league_id": s["league"].id,
            "league": s["league"].name,
            "platform": s["league"].platform.value if s["league"].platform else None,
            "week": s["week"],
            "team": s["team"].name,
            "record": f"{s['team'].wins}-{s['team'].losses}"
                      + (f"-{s['team'].ties}" if s["team"].ties else ""),
            "opponent": s["opponent"].name if s["opponent"] else None,
            "points": my_points,
            "opponent_points": their_points,
            "projected": my_proj,
            "opponent_projected": their_proj,
            "margin": margin,
            # A projected margin inside a touchdown is not a lead worth trusting.
            "status": "comfortable" if margin >= 15 else
                      "tight" if margin >= -15 else "behind",
            "alerts": hurt,
        })

    # Most precarious first: that is the league that needs attention.
    weeks.sort(key=lambda w: w["margin"])

    # ---- cross-league player index ------------------------------------------
    index: Dict[str, Dict[str, Any]] = {}

    def record(player: dict, s: dict, side: str) -> None:
        name = player.get("full_name")
        if not name:
            return
        key = news_service._name_key(name)
        entry = index.setdefault(key, {
            "name": name,
            "position": player.get("position_name"),
            "team": player.get("pro_team_abbr"),
            "player_id": player.get("player_id"),
            "for": [],
            "against": [],
        })
        entry[side].append(_entry(s["league"], s["team"] if side == "for" else s["opponent"], player))

    for s in active:
        for player in s["mine"]:
            record(player, s, "for")
        if s["opponent"]:
            for player in s["theirs"]:
                record(player, s, "against")

    def starting(entries: List[dict]) -> int:
        return sum(1 for e in entries if e["starting"])

    conflicts, exposure = [], []
    for entry in index.values():
        for_start, against_start = starting(entry["for"]), starting(entry["against"])

        # Only a starter on both sides is a real conflict; a bench player is
        # not doing anything to anybody.
        if for_start and against_start:
            conflicts.append({
                **entry,
                "for_count": for_start,
                "against_count": against_start,
                "net": for_start - against_start,
                "verdict": verdict(for_start, against_start),
            })

        # Owning him in two leagues only matters if he is actually in a lineup;
        # a player benched everywhere cannot hurt a Sunday at all.
        if len(entry["for"]) > 1 and for_start:
            exposure.append({
                **entry,
                "leagues": len(entry["for"]),
                "starting_in": for_start,
                "projected": round(
                    sum(e["projected"] for e in entry["for"] if e["starting"]), 1
                ),
            })

    # The most divided first — a genuine wash is more confusing than a lean.
    conflicts.sort(key=lambda c: (-min(c["for_count"], c["against_count"]), -c["for_count"]))
    # The most concentrated first — that is where a bust hurts most.
    exposure.sort(key=lambda e: (-e["starting_in"], -e["projected"]))

    return {
        "leagues": len(leagues),
        "teams": len(active),
        "unclaimed": unclaimed,
        "weeks": weeks,
        "conflicts": conflicts,
        "exposure": exposure,
        "totals": {
            "points": round(sum(w["points"] for w in weeks), 1),
            "projected": round(sum(w["projected"] for w in weeks), 1),
            "winning": sum(1 for w in weeks if w["margin"] > 0),
            "alerts": sum(len(w["alerts"]) for w in weeks),
        },
    }
