"""
Everything you own, across every league, in one place.

Playing in more than one league creates a situation no single-league view can
show you: the same player is on your roster in one league and on the roster of
the person you are playing in another. Every touchdown he scores helps you and
hurts you at the same time, and most people do not notice until they are
watching a game with no idea who to root for.

That conflict is the headline here. Underneath it sit the other things a
single-league view cannot answer — how exposed you are to one player across all
your teams, which of your weeks are actually in trouble, and which NFL games on
right now have anybody of yours in them. The last of those is Game Day widened
to every league at once: one screen that answers "what is happening to me right
now" without picking a league first.

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
from app.services import freshness, league_context, live_slate, news_service
from app.services.league_access import visible_to

logger = structlog.get_logger()
router = APIRouter(prefix="/portfolio", tags=["portfolio"])

UNAVAILABLE = live_slate.UNAVAILABLE
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


def _holding(entry: dict) -> dict:
    """One league's stake in a player, as the cross-league game card shows it."""
    return {
        "league_id": entry["league_id"],
        "league": entry["league"],
        "team": entry["team"],
        "slot": entry["slot"],
        "points": entry["points"],
        "projected": entry["projected"],
    }


def _slate_player(entry: dict, game_state: Optional[str]) -> dict:
    """A player on the live slate, with every league he is in it for.

    The same human can be your starter in one league and your opponent's in
    another, so he is one row carrying both sides rather than two rows. What he
    is worth differs per league — scoring settings differ — so the headline is
    the league with the biggest stake in him, points and projection together
    from that one league rather than the largest of each taken separately, and
    the per-league detail sits underneath.
    """
    for_rows = [_holding(e) for e in entry["for"] if e["starting"]]
    against_rows = [_holding(e) for e in entry["against"] if e["starting"]]
    stakes = for_rows + against_rows
    headline = max(stakes, key=lambda row: row["projected"], default=None)

    return {
        "name": entry["name"],
        "player_id": entry["player_id"],
        "position": entry["position"],
        "team": entry["team"],
        "injury_status": entry.get("injury_status"),
        "game_state": game_state,
        "points": headline["points"] if headline else 0.0,
        "projected": headline["projected"] if headline else 0.0,
        "for": for_rows,
        "against": against_rows,
        # Rooting for and against the same man at the same time.
        "conflict": bool(for_rows and against_rows),
    }


def _why_watch(players: List[dict]) -> str:
    """One line on why this game is worth your attention, across all leagues."""
    yours = sum(1 for p in players if p["for"])
    theirs = sum(1 for p in players if p["against"])
    split = sum(1 for p in players if p["conflict"])

    parts = []
    if yours:
        parts.append(f"{yours} of yours")
    if theirs:
        parts.append(f"{theirs} you are facing")
    if split:
        parts.append(f"{split} cutting both ways")
    return " · ".join(parts)


def _slate(index: Dict[str, Dict[str, Any]], games: List[dict]) -> List[dict]:
    """Every NFL game with somebody of yours in it, hardest-hitting first.

    A game nobody in any of your leagues is playing in is not a card; it is the
    reason a generic scoreboard is useless on a Sunday.
    """
    by_team = live_slate.index_by_pro_team(games)
    by_game: Dict[str, List[dict]] = {}

    for entry in index.values():
        game = by_team.get((entry.get("team") or "").upper())
        if not game:
            continue  # bye, free agent, or a team not on today's slate
        player = _slate_player(entry, game.get("state"))
        if not player["for"] and not player["against"]:
            continue  # on a bench everywhere, so doing nothing to anybody
        by_game.setdefault(game["id"], []).append(player)

    out = []
    for game in games:
        players = by_game.get(game["id"])
        if not players:
            continue
        # Conflicts first — they are the ones nobody notices on their own —
        # then by what is at stake.
        players.sort(key=lambda p: (not p["conflict"], -p["projected"]))
        contested = any(p["for"] for p in players) and any(p["against"] for p in players)
        # Every lineup he is in is a separate claim on the afternoon, so a
        # player started in three of your leagues weighs three times as much
        # here as one started in a single league.
        at_stake = sum(
            holding["projected"]
            for player in players
            for holding in player["for"] + player["against"]
        )
        out.append({
            **game,
            "players": players,
            "yours": sum(1 for p in players if p["for"]),
            "theirs": sum(1 for p in players if p["against"]),
            "conflicts": sum(1 for p in players if p["conflict"]),
            "why": _why_watch(players),
            "leverage": live_slate.leverage(game, at_stake, contested=contested),
        })

    out.sort(key=lambda g: -g["leverage"])
    return out


def _live_totals(slate: List[dict]) -> Dict[str, Any]:
    """The state of your whole Sunday, in the four numbers that matter."""
    mine_live = mine_pre = theirs_live = 0
    points_in_play = 0.0

    for game in slate:
        for player in game["players"]:
            running = game.get("state") == "in"
            pending = (
                game.get("state") == "pre"
                and player["injury_status"] not in UNAVAILABLE
            )
            if player["for"]:
                mine_live += 1 if running else 0
                mine_pre += 1 if pending else 0
                if running or pending:
                    # Every league he starts in is a separate pile of points
                    # still coming your way.
                    points_in_play += sum(r["projected"] for r in player["for"])
            if player["against"] and running:
                theirs_live += 1

    return {
        "games": sum(1 for g in slate if g.get("state") == "in"),
        "playing_now": mine_live,
        "yet_to_play": mine_pre,
        "theirs_playing_now": theirs_live,
        "points_in_play": round(points_in_play, 1),
    }


async def _league_setup(
    league: League, user: User, db: AsyncSession
) -> Optional[Dict[str, Any]]:
    """The database half of a league: which team is mine, and who else is here.

    Split from the network half deliberately. One AsyncSession cannot be used
    from two coroutines at once, so everything that touches the database runs
    one league at a time, and only the platform calls fan out.
    """
    team = await league_context.my_team(league, user, db)
    if not team:
        return None

    return {
        "league": league,
        "team": team,
        # Loaded here so the opponent lookup below needs no session of its own.
        "teams": await league_context.all_teams(league, db),
        "week": league.current_week or 1,
    }


async def _league_live(setup: Dict[str, Any]) -> Dict[str, Any]:
    """The network half: who I play this week, and both rosters.

    Touches no database, so these can all run at once.
    """
    league, team = setup["league"], setup["team"]
    opponent = await league_context.opponent_this_week(
        league, team, setup["week"], teams=setup["teams"]
    )

    mine, theirs = await asyncio.gather(
        league_context.roster_for(league, team),
        league_context.roster_for(league, opponent) if opponent else _empty(),
    )

    return {**setup, "opponent": opponent, "mine": mine, "theirs": theirs}


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
            .where(visible_to(current_user.id))
            .order_by(League.name)
        )
    ).scalars().all()

    # Everything database-backed happens here, one league at a time: bringing
    # anything that has aged out up to date, then reading who is who. Sharing
    # the request's session across concurrent coroutines fails the whole
    # request rather than merely going slow.
    setups = []
    for league in leagues:
        await freshness.ensure_fresh(league, db)
        setups.append(await _league_setup(league, current_user, db))

    # Leagues with no claimed team cannot contribute, and the UI should say why
    # rather than silently showing fewer leagues than the user has.
    unclaimed = [
        {"league_id": league.id, "name": league.name}
        for league, setup in zip(leagues, setups) if setup is None
    ]

    # The platform calls, on the other hand, are the slow part and touch no
    # database, so every league's rosters load at once.
    active = list(await asyncio.gather(*(_league_live(s) for s in setups if s)))

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
            "injury_status": player.get("injury_status"),
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

    # ---- the live slate, across every league --------------------------------
    # The scoreboard is one shared fetch (cached for a minute), so widening
    # Game Day to every league at once costs nothing the rosters above have not
    # already paid for.
    scoreboard = await news_service.fetch_scoreboard()
    slate = _slate(index, scoreboard)

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
        "games": slate,
        "live": _live_totals(slate),
        # Games nobody of yours is in are filtered out above; this is how many
        # there were, so the UI can tell "no slate yet" from "nobody playing".
        "slate_size": len(scoreboard),
    }
