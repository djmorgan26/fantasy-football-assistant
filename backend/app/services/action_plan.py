"""What to do about your roster this week, ranked.

A lineup hole does not announce itself. A.J. Brown going on IR turns a starting
slot into a guaranteed zero, and nothing in the app used to say so: the roster
page showed his status, and the rest was left to the manager to notice, work
out, and act on. This builds the whole chain instead - the hole, the bench
player who fills it, who is available to replace him properly, what to bid, and
which rosters would trade for the surplus that created.

Everything here is derived from real roster and league data and carries its own
numbers, so the prose layer on top has facts to quote and nothing to invent.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

import structlog

logger = structlog.get_logger()

# A player with one of these is not playing. DOUBTFUL is a risk, not a hole.
UNAVAILABLE = {"OUT", "INJURY_RESERVE", "IR", "SUSPENSION", "NA"}
RISKY = {"DOUBTFUL", "QUESTIONABLE"}

# Which positions may fill which starting slot. Both platforms' slot names are
# folded into one table so callers never branch on platform.
SLOT_ELIGIBILITY: Dict[str, frozenset] = {
    "QB": frozenset({"QB"}),
    "RB": frozenset({"RB"}),
    "WR": frozenset({"WR"}),
    "TE": frozenset({"TE"}),
    "K": frozenset({"K"}),
    "D/ST": frozenset({"D/ST", "DEF"}),
    "DEF": frozenset({"D/ST", "DEF"}),
    "FLEX": frozenset({"RB", "WR", "TE"}),
    "RB/WR": frozenset({"RB", "WR"}),
    "WR/TE": frozenset({"WR", "TE"}),
    "RB/WR/TE": frozenset({"RB", "WR", "TE"}),
    "SFLEX": frozenset({"QB", "RB", "WR", "TE"}),
    "SUPER_FLEX": frozenset({"QB", "RB", "WR", "TE"}),
    "OP": frozenset({"QB", "RB", "WR", "TE"}),
}

# How much of what is left it is reasonable to spend on one claim. A season-
# defining starter is worth a third of the budget; a depth flier is not.
FAAB_SHARE = {"critical": 0.35, "high": 0.2, "medium": 0.1, "low": 0.04}

# Below this a projection is the platform saying "no idea" or "will not play",
# and such a player must never be presented as a pickup.
MIN_USEFUL_PROJECTION = 1.0

# Two weekly projections inside this are the same forecast with rounding
# between them, so something other than the projection has to break the tie.
PROJECTION_NOISE = 1.5


def _points(player: Dict[str, Any], key: str = "projected_points") -> float:
    return float(player.get(key) or 0)


def eligible_for(slot: Optional[str], position: Optional[str]) -> bool:
    """Can this position start in this slot?

    An unknown slot falls back to an exact position match rather than allowing
    everyone: a wrong "yes" here recommends an illegal lineup.
    """
    if not slot or not position:
        return False
    allowed = SLOT_ELIGIBILITY.get(slot.upper())
    if allowed is None:
        return slot.upper() == position.upper()
    return position.upper() in allowed


def is_unavailable(player: Dict[str, Any]) -> bool:
    status = (player.get("injury_status") or "").upper()
    return bool(player.get("on_injured_reserve")) or status in UNAVAILABLE


def find_holes(roster: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Starting slots that will score nothing, worst first.

    A player on IR is a certain zero. A player listed OUT is the same thing for
    this week. Both are holes; QUESTIONABLE is reported separately as a risk,
    because benching a healthy-enough star is its own mistake.
    """
    holes = []
    for player in roster:
        if not player.get("is_starter"):
            continue
        if not is_unavailable(player):
            continue
        holes.append({
            "player": player.get("full_name"),
            "player_id": player.get("player_id"),
            "position": player.get("position_name"),
            "slot": player.get("lineup_slot_name"),
            "status": player.get("injury_status") or "INJURY_RESERVE",
            # What the slot is currently worth: nothing.
            "points_lost": round(_points(player), 1),
        })
    holes.sort(key=lambda h: h["points_lost"], reverse=True)
    return holes


def find_risks(roster: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Starters who might not play. Worth watching, not yet worth acting on."""
    return [
        {
            "player": p.get("full_name"),
            "slot": p.get("lineup_slot_name"),
            "status": p.get("injury_status"),
            "projected": round(_points(p), 1),
        }
        for p in roster
        if p.get("is_starter")
        and not is_unavailable(p)
        and (p.get("injury_status") or "").upper() in RISKY
    ]


def bench_options(
    hole: Dict[str, Any], roster: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Bench players who can legally fill this slot, best projection first.

    Anyone hurt themselves is left out: swapping one zero for another is not a
    fix, and offering it as one wastes the manager's attention.
    """
    options = [
        {
            "player": p.get("full_name"),
            "player_id": p.get("player_id"),
            "position": p.get("position_name"),
            "projected": round(_points(p), 1),
            "last_week": round(_points(p, "applied_points"), 1),
            "team": p.get("pro_team_abbr"),
        }
        for p in roster
        if not p.get("is_starter")
        and not p.get("on_injured_reserve")
        and not is_unavailable(p)
        and eligible_for(hole.get("slot"), p.get("position_name"))
    ]
    # Projection leads, but inside PROJECTION_NOISE the two are indistinguishable
    # forecasts and last week's actual is the better tiebreak. Sorting on
    # projection alone let a 0.1 edge outrank a man who scored 14 more points.
    options.sort(
        key=lambda o: (round(o["projected"] / PROJECTION_NOISE), o["last_week"]),
        reverse=True,
    )
    return options


def waiver_options(
    hole: Dict[str, Any],
    free_agents: Iterable[Dict[str, Any]],
    trending: Optional[Dict[str, int]] = None,
    limit: int = 4,
) -> List[Dict[str, Any]]:
    """Available players who could fill this slot.

    Sorted by projection, but carrying how many leagues added each one in the
    last day, because that is what decides whether a claim needs a real bid or
    can wait for the free waiver run.
    """
    trending = trending or {}
    out = []
    for fa in free_agents:
        if not eligible_for(hole.get("slot"), fa.get("position_name")):
            continue
        # A player the platform projects at zero is not an option, he is noise.
        # Offering four of them reads as advice and is worse than saying the
        # pool has nothing.
        if _points(fa) < MIN_USEFUL_PROJECTION:
            continue
        name = fa.get("full_name")
        out.append({
            "player": name,
            "player_id": fa.get("player_id"),
            "position": fa.get("position_name"),
            "team": fa.get("pro_team_abbr"),
            "projected": round(_points(fa), 1),
            "added_by": trending.get(name, 0),
            "contested": trending.get(name, 0) > 0,
        })
    out.sort(key=lambda o: (o["projected"], o["added_by"]), reverse=True)
    return out[:limit]


def faab_advice(
    remaining: Optional[float], total: Optional[float], urgency: str
) -> Optional[Dict[str, Any]]:
    """What to bid, as a share of what is left rather than of the season.

    Budget spent is gone; only what remains can be bid. A share of the remaining
    pot therefore stays sane late in the year, when a third of the original
    budget may be more than the manager still holds.
    """
    if remaining is None or total is None or total <= 0:
        return None

    share = FAAB_SHARE.get(urgency, FAAB_SHARE["medium"])
    bid = int(round(remaining * share))
    return {
        "remaining": round(remaining, 1),
        "total": round(total, 1),
        "spent_pct": round(100 * (total - remaining) / total),
        # A dollar is the smallest meaningful claim; never advise bidding zero
        # on something worth claiming.
        "suggested_bid": max(1, bid) if remaining >= 1 else 0,
        "max_sensible": int(round(remaining * 0.5)),
        "note": (
            "Nothing left to bid; this has to be a free-agent claim."
            if remaining < 1 else None
        ),
    }


def positional_depth(roster: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Startable bodies per position, and what the depth is worth.

    Counts only players who can actually play: an injured backup is not depth,
    which is exactly the mistake that makes a roster look fine on paper while
    one more injury guts it.
    """
    depth: Dict[str, Dict[str, Any]] = {}
    for player in roster:
        pos = (player.get("position_name") or "").upper()
        if not pos or is_unavailable(player):
            continue
        entry = depth.setdefault(pos, {"count": 0, "starters": 0, "bench_points": 0.0})
        entry["count"] += 1
        if player.get("is_starter"):
            entry["starters"] += 1
        else:
            entry["bench_points"] += _points(player)
    for entry in depth.values():
        entry["bench_points"] = round(entry["bench_points"], 1)
    return depth


def trade_angles(
    mine: Dict[str, Dict[str, Any]],
    others: Sequence[Dict[str, Any]],
    need: Optional[str],
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """Teams whose shape is the mirror of yours.

    A trade only happens when both sides fix something. The useful pairing is a
    team deep where you are thin and thin where you are deep, so the search is
    for that mirror rather than for the best player available.
    """
    if not need:
        return []

    surplus = sorted(
        (pos for pos, d in mine.items() if d["count"] - d["starters"] >= 2),
        key=lambda pos: mine[pos]["bench_points"],
        reverse=True,
    )
    if not surplus:
        return []

    angles = []
    for other in others:
        their = other.get("depth") or {}
        their_need = [pos for pos in surplus if their.get(pos, {}).get("count", 0) <= 1]
        their_spare = (their.get(need, {}).get("count", 0)
                       - their.get(need, {}).get("starters", 0))
        if their_need and their_spare >= 1:
            angles.append({
                "team": other.get("team"),
                "they_need": their_need[0],
                "they_can_spare": need,
                "your_surplus_points": mine[their_need[0]]["bench_points"],
            })

    angles.sort(key=lambda a: a["your_surplus_points"], reverse=True)
    return angles[:limit]


def urgency_for(hole: Dict[str, Any], best_bench: Optional[Dict[str, Any]]) -> str:
    """How badly this needs outside help.

    The question is not how good the injured player was, it is how big the drop
    to the best replacement already on the roster is. A deep bench turns a star
    injury into an inconvenience; an empty one turns it into a lost week.
    """
    lost = hole.get("points_lost") or 0
    covered = best_bench["projected"] if best_bench else 0.0
    gap = lost - covered

    if not best_bench:
        return "critical"   # the slot cannot legally be filled from the bench
    if gap >= 8:
        return "high"
    if gap >= 3:
        return "medium"
    return "low"
