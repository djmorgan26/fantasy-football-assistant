"""The maths behind "should I do this trade".

Deliberately free of I/O. Everything here takes plain dicts and returns plain
dicts, so the whole model is unit-testable without a database, a league, or a
network. The callers in `api/trades.py` do the fetching.

Three ideas carry the feature:

1. **Value over replacement.** A player's raw projection says nothing on its
   own. 12 points a week is a great TE and a bad RB; what matters is the
   margin over the worst player you would still have to start at that position,
   which depends on league size and starting slots. `replacement_levels`
   computes that baseline from the actual player pool.

2. **Lineup impact.** Value is theoretical; the points you score are whatever
   your *optimal starting lineup* produces. `optimal_lineup` recomputes the best
   legal lineup before and after a trade, which is the only way to notice that a
   third good RB adds nothing when you can only start two, or that a trade for a
   better TE is worth more than its raw value because your current TE is unstartable.

3. **Playoff odds.** The number a manager actually wants. `simulate_season`
   plays the rest of the schedule a few thousand times, drawing each team's
   weekly score from a normal around its optimal-lineup projection, and reports
   how often the team makes the cut. Run before and after, the delta is the
   trade's real cost or benefit.
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import structlog

logger = structlog.get_logger()

# The positions a fantasy roster is built from.
POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")

# Which positions may fill a generic FLEX slot.
FLEX_ELIGIBLE = ("RB", "WR", "TE")

# SUPER_FLEX additionally takes a QB.
SUPERFLEX_ELIGIBLE = ("QB", "RB", "WR", "TE")

# Used when a league tells us nothing about its lineup.
DEFAULT_SLOT_COUNTS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "K": 1, "DEF": 1}
DEFAULT_FLEX = 1

# Week-to-week fantasy scoring is noisy. This is the standard deviation of a
# team's weekly total as a fraction of its mean, taken from the historical
# spread of NFL team fantasy totals. It drives how much the simulation lets an
# underdog win, so it matters more than it looks: too low and the sim declares
# the standings already settled, too high and every trade looks irrelevant.
TEAM_SCORE_CV = 0.26

# Enough iterations that the odds are stable to roughly half a point, while
# still returning inside a request.
DEFAULT_ITERATIONS = 2000

# ESPN keys `lineupSlotCounts` by numeric slot id, not by name, so a league's
# starting requirements arrive as {"0": 1, "2": 2, "23": 1}. The mock league and
# Sleeper both use names, hence both spellings are accepted below.
ESPN_SLOT_IDS = {
    0: "QB", 2: "RB", 4: "WR", 6: "TE", 16: "DEF", 17: "K",
    23: "FLEX", 7: "SUPER_FLEX",
    # Slots that do not start anyone.
    20: "BENCH", 21: "IR",
}

# Aliases platforms use for the same position.
_POSITION_ALIASES = {
    "D/ST": "DEF",
    "DST": "DEF",
    "DEF": "DEF",
    "PK": "K",
    "K": "K",
    "FB": "RB",
    "HB": "RB",
    "WR/TE": "WR",
    "RB/WR": "RB",
}


def normalize_position(name: Optional[str]) -> str:
    """Canonical position for a player, across ESPN and Sleeper spellings."""
    if not name:
        return "UNKNOWN"
    key = str(name).strip().upper()
    if key in _POSITION_ALIASES:
        return _POSITION_ALIASES[key]
    return key if key in POSITIONS else key


@dataclass(frozen=True)
class LineupSlots:
    """How many of each position a team must start, plus its flex slots."""

    counts: Dict[str, int] = field(default_factory=lambda: dict(DEFAULT_SLOT_COUNTS))
    flex: int = DEFAULT_FLEX
    superflex: int = 0

    @property
    def total_starters(self) -> int:
        return sum(self.counts.values()) + self.flex + self.superflex


def lineup_slots_from_settings(
    roster_settings: Optional[Dict[str, Any]],
    roster_positions: Optional[Sequence[str]] = None,
) -> LineupSlots:
    """Read a league's starting requirements out of whatever it happens to carry.

    Sleeper hands us `roster_positions`, a flat list with one entry per slot
    ("QB", "RB", "RB", "FLEX", "BN", ...). ESPN hands us `roster_settings`
    with a `lineup_slots` mapping of name to count. Either is enough; neither
    being present falls back to a standard lineup rather than failing, because a
    slightly wrong baseline is far better than no analysis.
    """
    counts: Dict[str, int] = {p: 0 for p in POSITIONS}
    flex = 0
    superflex = 0

    if roster_positions:
        for slot in roster_positions:
            canonical = normalize_position(slot)
            if canonical in counts:
                counts[canonical] += 1
            elif str(slot).upper() in ("FLEX", "WRRB_FLEX", "REC_FLEX", "WRRB"):
                flex += 1
            elif str(slot).upper() in ("SUPER_FLEX", "SUPERFLEX", "QB/RB/WR/TE"):
                superflex += 1
    elif roster_settings:
        raw = roster_settings.get("lineup_slots") or {}
        for slot, count in raw.items():
            try:
                count = int(count)
            except (TypeError, ValueError):
                continue
            # A numeric key is an ESPN slot id; a named one is already a name.
            name = str(slot)
            if name.lstrip("-").isdigit():
                name = ESPN_SLOT_IDS.get(int(name), "")
            if name in ("BENCH", "IR", ""):
                continue

            canonical = normalize_position(name)
            if canonical in counts:
                counts[canonical] += count
            elif name.upper() in ("FLEX", "RB/WR/TE", "WR/RB"):
                flex += count
            elif name.upper() in ("SUPER_FLEX", "SUPERFLEX"):
                superflex += count

    if sum(counts.values()) == 0:
        return LineupSlots(dict(DEFAULT_SLOT_COUNTS), max(flex, DEFAULT_FLEX), superflex)
    return LineupSlots({k: v for k, v in counts.items() if v}, flex, superflex)


def player_points(player: Dict[str, Any]) -> float:
    """A player's weekly expected points, from whichever field carries it.

    Rosters arrive ESPN-shaped from `league_context.roster_for`, where
    `projected_points` is the forward-looking number and `applied_points` is
    what actually happened. Projection wins; a player with neither is a zero,
    not a crash.
    """
    for key in ("projected_points", "applied_points", "season_points"):
        value = player.get(key)
        if isinstance(value, (int, float)) and value:
            return float(value)
    return 0.0


def optimal_lineup(
    players: Iterable[Dict[str, Any]], slots: LineupSlots
) -> Tuple[float, List[Dict[str, Any]]]:
    """The best legal starting lineup from a set of players, and what it scores.

    Greedy by descending points, filling dedicated slots first and flex slots
    from what is left. Greedy is optimal here because every slot's eligibility
    set is either a single position or a superset of the flex positions, so
    taking the best available at each dedicated slot can never strand a better
    flex option than it gains.

    Players on IR are excluded. They cannot be started, so counting them
    inflates every lineup they appear in.
    """
    available = [p for p in players if not p.get("on_injured_reserve")]
    by_position: Dict[str, List[Dict[str, Any]]] = {}
    for player in available:
        by_position.setdefault(normalize_position(player.get("position_name")), []).append(player)
    for bucket in by_position.values():
        bucket.sort(key=player_points, reverse=True)

    chosen: List[Dict[str, Any]] = []
    used: set = set()

    def take(pool: List[Dict[str, Any]], slot_name: str) -> bool:
        for candidate in pool:
            key = id(candidate)
            if key in used:
                continue
            used.add(key)
            chosen.append({**candidate, "filled_slot": slot_name})
            return True
        return False

    for position, count in slots.counts.items():
        pool = by_position.get(position, [])
        for _ in range(count):
            take(pool, position)

    def flex_pool(eligible: Sequence[str]) -> List[Dict[str, Any]]:
        pool = [p for pos in eligible for p in by_position.get(pos, []) if id(p) not in used]
        pool.sort(key=player_points, reverse=True)
        return pool

    for _ in range(slots.flex):
        take(flex_pool(FLEX_ELIGIBLE), "FLEX")
    for _ in range(slots.superflex):
        take(flex_pool(SUPERFLEX_ELIGIBLE), "SUPER_FLEX")

    total = round(sum(player_points(p) for p in chosen), 2)
    return total, chosen


def replacement_levels(
    league_players: Iterable[Dict[str, Any]],
    slots: LineupSlots,
    team_count: int,
) -> Dict[str, float]:
    """The points a freely-available starter scores, per position.

    The baseline is the (starters x teams)-th best player at that position: the
    last one who would be starting somewhere if every team started optimally.
    Anyone below that line is replaceable, which is why a WR4's raw projection
    overstates what he is worth in a trade.

    FLEX slots are spread across RB/WR/TE in the proportions leagues actually
    flex them, which pushes those baselines down (correctly, because a flex slot means
    one more RB is startable league-wide).
    """
    flex_share = {"RB": 0.45, "WR": 0.45, "TE": 0.10}
    by_position: Dict[str, List[float]] = {}
    for player in league_players:
        position = normalize_position(player.get("position_name"))
        by_position.setdefault(position, []).append(player_points(player))

    levels: Dict[str, float] = {}
    for position in POSITIONS:
        points = sorted(by_position.get(position, []), reverse=True)
        if not points:
            levels[position] = 0.0
            continue

        starters = slots.counts.get(position, 0)
        extra = slots.flex * flex_share.get(position, 0.0)
        if position in SUPERFLEX_ELIGIBLE:
            extra += slots.superflex * (0.6 if position == "QB" else 0.13)
        rank = max(1, int(round((starters + extra) * team_count)))
        levels[position] = round(points[min(rank, len(points)) - 1], 2)
    return levels


def value_over_replacement(
    player: Dict[str, Any], levels: Dict[str, float]
) -> float:
    """How much better this player is than a startable replacement, per week.

    Floored at zero: a player worse than replacement is worth nothing in a
    trade, not a negative, because the alternative is simply not rostering him.
    """
    position = normalize_position(player.get("position_name"))
    return round(max(0.0, player_points(player) - levels.get(position, 0.0)), 2)


def position_depth(
    players: Iterable[Dict[str, Any]], slots: LineupSlots, levels: Dict[str, float]
) -> Dict[str, Dict[str, Any]]:
    """Startable bodies per position against what the lineup requires.

    "Startable" means above replacement level. A team with four RBs and a
    required two is not deep if two of them are below the line.
    """
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for player in players:
        if player.get("on_injured_reserve"):
            continue
        buckets.setdefault(normalize_position(player.get("position_name")), []).append(player)

    depth: Dict[str, Dict[str, Any]] = {}
    for position in POSITIONS:
        bucket = sorted(buckets.get(position, []), key=player_points, reverse=True)
        startable = sum(1 for p in bucket if player_points(p) >= levels.get(position, 0.0))
        required = slots.counts.get(position, 0)
        depth[position] = {
            "rostered": len(bucket),
            "startable": startable,
            "required": required,
            "surplus": startable - required,
            "best": round(player_points(bucket[0]), 2) if bucket else 0.0,
        }
    return depth


@dataclass
class SideImpact:
    """What a trade does to one team."""

    team_id: int
    team_name: str
    lineup_before: float
    lineup_after: float
    value_out: float
    value_in: float
    depth_before: Dict[str, Dict[str, Any]]
    depth_after: Dict[str, Dict[str, Any]]

    @property
    def lineup_delta(self) -> float:
        return round(self.lineup_after - self.lineup_before, 2)

    @property
    def value_delta(self) -> float:
        return round(self.value_in - self.value_out, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "lineup_before": self.lineup_before,
            "lineup_after": self.lineup_after,
            "lineup_delta": self.lineup_delta,
            "value_out": self.value_out,
            "value_in": self.value_in,
            "value_delta": self.value_delta,
            "depth_before": self.depth_before,
            "depth_after": self.depth_after,
        }


def evaluate_side(
    *,
    team_id: int,
    team_name: str,
    roster: Sequence[Dict[str, Any]],
    outgoing_ids: Sequence[Any],
    incoming: Sequence[Dict[str, Any]],
    slots: LineupSlots,
    levels: Dict[str, float],
) -> SideImpact:
    """Recompute one team's lineup and depth as if the trade had happened."""
    outgoing = {str(pid) for pid in outgoing_ids}
    kept = [p for p in roster if str(p.get("player_id")) not in outgoing]
    gone = [p for p in roster if str(p.get("player_id")) in outgoing]
    after = kept + list(incoming)

    before_points, _ = optimal_lineup(roster, slots)
    after_points, _ = optimal_lineup(after, slots)

    return SideImpact(
        team_id=team_id,
        team_name=team_name,
        lineup_before=before_points,
        lineup_after=after_points,
        value_out=round(sum(value_over_replacement(p, levels) for p in gone), 2),
        value_in=round(sum(value_over_replacement(p, levels) for p in incoming), 2),
        depth_before=position_depth(roster, slots, levels),
        depth_after=position_depth(after, slots, levels),
    )


def fairness_score(side_a: SideImpact, side_b: SideImpact) -> float:
    """0-100, where 100 is a dead-even swap of value.

    Scored on the *share* of total value each side receives rather than the raw
    gap, so a 2-point edge in a 10-point trade is correctly treated as lopsided
    while the same gap in a 60-point blockbuster is not.
    """
    total = side_a.value_in + side_b.value_in
    if total <= 0:
        return 50.0
    share = side_a.value_in / total
    return round(max(0.0, 100.0 - abs(share - 0.5) * 200.0), 1)


# ---------------------------------------------------------------------------
# Season simulation
# ---------------------------------------------------------------------------


@dataclass
class SimTeam:
    team_id: int
    name: str
    wins: float
    losses: float
    points_for: float
    weekly_mean: float


def simulate_season(
    teams: Sequence[SimTeam],
    schedule: Sequence[Sequence[Tuple[int, int]]],
    playoff_spots: int,
    iterations: int = DEFAULT_ITERATIONS,
    seed: Optional[int] = None,
) -> Dict[int, float]:
    """Playoff probability per team, from Monte Carlo over the real schedule.

    Each team's weekly score is drawn from a normal around its optimal-lineup
    projection with a spread of `TEAM_SCORE_CV`. Seeding ties break on points
    for, which is what most leagues do and, more importantly, is what makes a
    high-scoring team's odds respond to a trade that adds points without
    obviously adding wins.

    `schedule` is a list of weeks, each a list of (team_id, team_id) pairings.
    An empty schedule means the season is over: current records decide it, and
    the odds come back as a clean 1 or 0.
    """
    rng = random.Random(seed)
    index = {t.team_id: t for t in teams}
    made: Dict[int, int] = {t.team_id: 0 for t in teams}
    if not teams:
        return {}

    for _ in range(max(1, iterations)):
        wins = {t.team_id: t.wins for t in teams}
        points = {t.team_id: t.points_for for t in teams}

        for week in schedule:
            for home_id, away_id in week:
                home, away = index.get(home_id), index.get(away_id)
                if home is None or away is None:
                    continue
                home_score = rng.gauss(home.weekly_mean, home.weekly_mean * TEAM_SCORE_CV)
                away_score = rng.gauss(away.weekly_mean, away.weekly_mean * TEAM_SCORE_CV)
                points[home_id] += home_score
                points[away_id] += away_score
                if home_score >= away_score:
                    wins[home_id] += 1
                else:
                    wins[away_id] += 1

        standings = sorted(
            (t.team_id for t in teams),
            key=lambda tid: (wins[tid], points[tid]),
            reverse=True,
        )
        for team_id in standings[:playoff_spots]:
            made[team_id] += 1

    total = max(1, iterations)
    return {tid: round(100.0 * count / total, 1) for tid, count in made.items()}


# ---------------------------------------------------------------------------
# Opportunity finder
# ---------------------------------------------------------------------------


@dataclass
class TradeIdea:
    partner_team_id: int
    partner_team_name: str
    give: List[Dict[str, Any]]
    receive: List[Dict[str, Any]]
    my_lineup_delta: float
    their_lineup_delta: float
    fairness: float

    @property
    def mutual_gain(self) -> float:
        return round(self.my_lineup_delta + self.their_lineup_delta, 2)

    def to_dict(self) -> Dict[str, Any]:
        def brief(player: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "player_id": str(player.get("player_id")),
                "full_name": player.get("full_name"),
                "position": normalize_position(player.get("position_name")),
                "pro_team": player.get("pro_team_abbr"),
                "projected_points": round(player_points(player), 2),
                "injury_status": player.get("injury_status"),
            }

        return {
            "partner_team_id": self.partner_team_id,
            "partner_team_name": self.partner_team_name,
            "give": [brief(p) for p in self.give],
            "receive": [brief(p) for p in self.receive],
            "my_lineup_delta": self.my_lineup_delta,
            "their_lineup_delta": self.their_lineup_delta,
            "mutual_gain": self.mutual_gain,
            "fairness": self.fairness,
        }


def find_opportunities(
    *,
    my_team_id: int,
    my_roster: Sequence[Dict[str, Any]],
    other_rosters: Dict[int, Sequence[Dict[str, Any]]],
    team_names: Dict[int, str],
    slots: LineupSlots,
    levels: Dict[str, float],
    limit: int = 12,
    max_candidates_per_side: int = 8,
) -> List[TradeIdea]:
    """Trades that make *both* teams better, ranked by how much.

    The insight a trade finder needs is that lineup improvement is not zero-sum.
    Two teams with mirrored surpluses (you are three deep at RB and thin at TE,
    they are the reverse) can each raise their starting lineup by swapping, and
    that is the trade the other manager will actually accept. Ranking by the
    *sum* of both deltas surfaces those, while requiring both to be positive
    filters out the fleeces nobody says yes to.

    Only 1-for-1 swaps are enumerated, from each side's most tradeable players
    (surplus first). The combinatorics of larger packages explode, and in
    practice a 1-for-1 that both sides gain from is the opening offer anyway.
    """
    ideas: List[TradeIdea] = []
    my_candidates = _tradeable(my_roster, slots, levels, max_candidates_per_side)

    for partner_id, partner_roster in other_rosters.items():
        if partner_id == my_team_id:
            continue
        their_candidates = _tradeable(partner_roster, slots, levels, max_candidates_per_side)

        for mine in my_candidates:
            for theirs in their_candidates:
                if normalize_position(mine.get("position_name")) == normalize_position(
                    theirs.get("position_name")
                ) and abs(player_points(mine) - player_points(theirs)) < 1.0:
                    continue  # a wash, not a trade

                my_side = evaluate_side(
                    team_id=my_team_id,
                    team_name=team_names.get(my_team_id, "You"),
                    roster=my_roster,
                    outgoing_ids=[mine.get("player_id")],
                    incoming=[theirs],
                    slots=slots,
                    levels=levels,
                )
                if my_side.lineup_delta <= 0:
                    continue

                their_side = evaluate_side(
                    team_id=partner_id,
                    team_name=team_names.get(partner_id, "Them"),
                    roster=partner_roster,
                    outgoing_ids=[theirs.get("player_id")],
                    incoming=[mine],
                    slots=slots,
                    levels=levels,
                )
                if their_side.lineup_delta <= 0:
                    continue

                ideas.append(
                    TradeIdea(
                        partner_team_id=partner_id,
                        partner_team_name=team_names.get(partner_id, "Them"),
                        give=[mine],
                        receive=[theirs],
                        my_lineup_delta=my_side.lineup_delta,
                        their_lineup_delta=their_side.lineup_delta,
                        fairness=fairness_score(my_side, their_side),
                    )
                )

    ideas.sort(key=lambda i: (i.my_lineup_delta, i.mutual_gain), reverse=True)
    return ideas[:limit]


def _tradeable(
    roster: Sequence[Dict[str, Any]],
    slots: LineupSlots,
    levels: Dict[str, float],
    limit: int,
) -> List[Dict[str, Any]]:
    """The players a team would plausibly move: its surplus, best first.

    A team trades from depth. Players at a position where it already has more
    startable bodies than it can start are the ones on the block, so those sort
    ahead of everyone else.
    """
    depth = position_depth(roster, slots, levels)
    healthy = [p for p in roster if not p.get("on_injured_reserve")]

    def rank(player: Dict[str, Any]) -> Tuple[int, float]:
        position = normalize_position(player.get("position_name"))
        surplus = depth.get(position, {}).get("surplus", 0)
        return (1 if surplus > 0 else 0, player_points(player))

    return sorted(healthy, key=rank, reverse=True)[:limit]


def verdict_label(
    lineup_delta: float, odds_delta: Optional[float], fairness: float
) -> Tuple[str, str]:
    """A one-word call plus the reason, from the numbers rather than a vibe.

    Playoff odds lead when the simulation ran, because a trade that costs
    weekly points can still be right if it raises the odds (and vice versa).
    Lineup delta is the fallback when there is no schedule left to simulate.
    """
    if odds_delta is not None and abs(odds_delta) >= 1.0:
        if odds_delta >= 5:
            return "accept", f"Raises your playoff odds by {odds_delta:+.1f} points."
        if odds_delta >= 1:
            return "lean_accept", f"Nudges your playoff odds {odds_delta:+.1f} points."
        if odds_delta <= -5:
            return "reject", f"Costs you {abs(odds_delta):.1f} points of playoff odds."
        return "lean_reject", f"Slightly lowers your playoff odds ({odds_delta:+.1f})."

    if lineup_delta >= 3:
        return "accept", f"Adds {lineup_delta:+.1f} points a week to your starting lineup."
    if lineup_delta >= 0.5:
        return "lean_accept", f"Adds {lineup_delta:+.1f} points a week to your lineup."
    if lineup_delta <= -3:
        return "reject", f"Costs your lineup {abs(lineup_delta):.1f} points a week."
    if lineup_delta <= -0.5:
        return "lean_reject", f"Costs your lineup {abs(lineup_delta):.1f} points a week."
    return "neutral", f"Close to a wash ({lineup_delta:+.1f} points a week, fairness {fairness:.0f}/100)."
