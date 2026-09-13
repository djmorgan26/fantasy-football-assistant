"""
Game day: what is happening right now, for you and the person you are playing.

The question this answers is the one people actually open a fantasy app to ask
on a Sunday afternoon — *who do I still have left, and who do they still have?*
A generic scoreboard cannot answer it, because it does not know which sixteen
of those hundred players are yours and which are your opponent's.

Every game is scored for how much it matters to **this** matchup, so the slate
sorts by leverage rather than by kickoff time.
"""
import asyncio
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.db.database import get_database
from app.models.team import Team
from app.models.user import User
from app.services import league_context, news_service

logger = structlog.get_logger()
router = APIRouter(prefix="/gameday", tags=["gameday"])

# Statuses that mean a player will not take the field, so his points are gone
# rather than pending.
UNAVAILABLE = {"OUT", "INJURY_RESERVE", "IR", "SUSPENSION"}


def _player_view(player: dict, *, game_state: Optional[str]) -> dict:
    """One player as the game-day list shows him."""
    return {
        "player_id": player.get("player_id"),
        "name": player.get("full_name"),
        "position": player.get("position_name"),
        "slot": player.get("lineup_slot_name"),
        "team": player.get("pro_team_abbr"),
        "projected": round(player.get("projected_points") or 0, 1),
        "points": round(player.get("applied_points") or 0, 1),
        "injury_status": player.get("injury_status"),
        # pre → hasn't played, in → on the field, post → done, None → no game
        "game_state": game_state,
    }


def _index_games(games: List[dict]) -> Dict[str, dict]:
    """Map each pro team abbreviation to the game it is playing in."""
    by_team: Dict[str, dict] = {}
    for game in games:
        for side in ("home", "away"):
            abbr = (game.get(side) or {}).get("abbr")
            if abbr:
                by_team[abbr.upper()] = game
    return by_team


def _starters(roster: List[dict]) -> List[dict]:
    return [p for p in roster if p.get("is_starter")]


def _summarize(players: List[dict]) -> dict:
    """Where a side's points stand: banked, on the field, still to come."""
    playing = [p for p in players if p["game_state"] == "in"]
    yet_to_play = [
        p for p in players
        if p["game_state"] == "pre"
        and p.get("injury_status") not in UNAVAILABLE
    ]
    done = [p for p in players if p["game_state"] == "post"]

    return {
        "playing_now": len(playing),
        "yet_to_play": len(yet_to_play),
        "finished": len(done),
        "points": round(sum(p["points"] for p in players), 1),
        # The number that actually settles a Sunday argument: how much is still
        # in play, whether on the field or not yet kicked off.
        "points_in_play": round(
            sum(p["projected"] for p in playing + yet_to_play), 1
        ),
        "projected_total": round(sum(p["projected"] for p in players), 1),
    }


def _why_watch(mine: List[dict], theirs: List[dict]) -> str:
    """A short reason this game matters to this matchup."""
    def phrase(players: List[dict], who: str) -> str:
        if not players:
            return ""
        if len(players) == 1:
            return f"{who} {players[0]['name']}"
        return f"{who} {len(players)} starters"

    if mine and theirs:
        return f"{phrase(mine, 'You have')} against {phrase(theirs, 'their')}"
    if mine:
        return phrase(mine, "You have")
    if theirs:
        return phrase(theirs, "They have")
    return ""


def _leverage(game: dict, mine: List[dict], theirs: List[dict]) -> float:
    """How much this game decides the matchup.

    A game where both sides have players swings the margin twice as fast as one
    where only you do, so it is weighted accordingly. Points still to come
    matter more than points already banked, and a live game outranks one that
    has not kicked off.
    """
    at_stake = sum(p["projected"] for p in mine) + sum(p["projected"] for p in theirs)
    if not at_stake:
        return 0.0

    both_sides = 2.0 if (mine and theirs) else 1.0
    state_weight = {"in": 3.0, "pre": 2.0, "post": 1.0}.get(game.get("state"), 1.0)
    return round(at_stake * both_sides * state_weight, 2)


@router.get("/{league_id}")
async def game_day(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
) -> Dict[str, Any]:
    league = await league_context.load_league(league_id, current_user, db)

    team = await league_context.my_team(league, current_user, db)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Claim your team first to see game day.",
        )

    week = league.current_week or 1
    opponent: Optional[Team] = await league_context.opponent_this_week(
        league, team, week, db
    )

    my_roster, their_roster, games = await asyncio.gather(
        league_context.roster_for(league, team),
        league_context.roster_for(league, opponent) if opponent else _none_list(),
        news_service.fetch_scoreboard(),
    )

    by_team = _index_games(games)

    def views(roster: List[dict]) -> List[dict]:
        out = []
        for player in _starters(roster):
            game = by_team.get((player.get("pro_team_abbr") or "").upper())
            out.append(_player_view(player, game_state=game.get("state") if game else None))
        return out

    mine = views(my_roster)
    theirs = views(their_roster)

    # Attach each side's players to the game they are playing in.
    mine_by_game: Dict[str, List[dict]] = {}
    theirs_by_game: Dict[str, List[dict]] = {}
    for players, bucket in ((mine, mine_by_game), (theirs, theirs_by_game)):
        for player in players:
            game = by_team.get((player.get("team") or "").upper())
            if game:
                bucket.setdefault(game["id"], []).append(player)

    enriched = []
    for game in games:
        game_mine = mine_by_game.get(game["id"], [])
        game_theirs = theirs_by_game.get(game["id"], [])
        if not game_mine and not game_theirs:
            continue  # nobody in this matchup is in it; not worth a card
        enriched.append({
            **game,
            "mine": game_mine,
            "theirs": game_theirs,
            "why": _why_watch(game_mine, game_theirs),
            "leverage": _leverage(game, game_mine, game_theirs),
        })

    enriched.sort(key=lambda g: -g["leverage"])

    return {
        "week": week,
        "my_team": {
            "name": team.name,
            "summary": _summarize(mine),
            "players": mine,
        },
        "opponent": {
            "name": opponent.name if opponent else None,
            "summary": _summarize(theirs),
            "players": theirs,
        } if opponent else None,
        "games": enriched,
        # Nobody's players are in any game — a bye-heavy week, or the slate has
        # not been published yet. The UI says so rather than showing an empty list.
        "slate_size": len(games),
    }


async def _none_list() -> List[dict]:
    """Stand-in awaitable so gather() stays symmetrical with no opponent."""
    return []
