"""Mapping the live NFL slate onto fantasy rosters.

Two views ask the scoreboard the same question — *which of the players on the
field right now are somebody's?* — and differ only in whose. Game Day asks it of
one league's matchup; the cross-league view asks it of every team you run at
once. The join and the ranking live here so both answer it the same way.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Statuses that mean a player will not take the field, so his points are gone
# rather than pending.
UNAVAILABLE = {"OUT", "INJURY_RESERVE", "IR", "SUSPENSION"}

# A game being played decides more of the afternoon than one that has not
# kicked off, which in turn decides more than one already in the books.
STATE_WEIGHT = {"in": 3.0, "pre": 2.0, "post": 1.0}


def index_by_pro_team(games: List[dict]) -> Dict[str, dict]:
    """Map each pro team abbreviation to the game it is playing in."""
    by_team: Dict[str, dict] = {}
    for game in games:
        for side in ("home", "away"):
            abbr = (game.get(side) or {}).get("abbr")
            if abbr:
                by_team[abbr.upper()] = game
    return by_team


def game_state_for(by_team: Dict[str, dict], abbr: Optional[str]) -> Optional[str]:
    """`pre`, `in`, `post` — or None when the player's team is not on the slate."""
    game = by_team.get((abbr or "").upper())
    return game.get("state") if game else None


def leverage(game: Dict[str, Any], at_stake: float, contested: bool) -> float:
    """How much a game decides the matchup it is being watched for.

    A game where both sides have players swings the margin twice as fast as one
    where only you do, so it is weighted accordingly. Points still to come
    matter more than points already banked, and a live game outranks one that
    has not kicked off.
    """
    if not at_stake:
        return 0.0
    both_sides = 2.0 if contested else 1.0
    return round(at_stake * both_sides * STATE_WEIGHT.get(game.get("state"), 1.0), 2)
