"""
Mock data for MOCK_MODE (demo mode).

This module is the single source of truth for the realistic sample data used when
the app runs without any external credentials (MOCK_MODE=true). One coherent
fixture league powers BOTH the ESPN-flavored views (Press Box / content engine)
and the Sleeper-flavored views (Draft Room), so scores, rosters, teams and
narratives all line up no matter which feature you open.

Everything here is fully deterministic (no randomness, no network), so the same
demo always renders the same data. The service layer (ESPNService /
SleeperService) short-circuits to these builders when settings.mock_mode is on.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------- IDs

MOCK_ESPN_LEAGUE_ID = 1188291
MOCK_SLEEPER_LEAGUE_ID = "mock_sleeper_league"
MOCK_SLEEPER_USER_ID = "mock_user_you"
MOCK_SLEEPER_DRAFT_ID = "mock_draft_2025"

MOCK_SEASON = 2025
MOCK_CURRENT_WEEK = 14  # weeks 1..13 are "complete"; demo content uses week 13

DEMO_USER_EMAIL = "demo@demo.app"
DEMO_USER_PASSWORD = "demo1234"
DEMO_USER_NAME = "Demo Manager"

LEAGUE_NAME = "The Sunday Scaries Dynasty"

# ----------------------------------------------------------- the 10 league teams
# id, owner first name, team name, abbrev. Team 5 is "you" (the demo user).
TEAMS: List[Dict[str, Any]] = [
    {"id": 1, "owner": "Marcus", "name": "Game of Throws", "abbrev": "GOT"},
    {"id": 2, "owner": "Priya", "name": "Bench Warmers Anonymous", "abbrev": "BWA"},
    {"id": 3, "owner": "Diego", "name": "Multiple Scoregasms", "abbrev": "MSG"},
    {"id": 4, "owner": "Sam", "name": "The Replacements", "abbrev": "REP"},
    {"id": 5, "owner": "You", "name": "Comeback Cats", "abbrev": "CAT"},
    {"id": 6, "owner": "Tasha", "name": "Pain Train", "abbrev": "PAIN"},
    {"id": 7, "owner": "Kev", "name": "Show Me Your TDs", "abbrev": "TDS"},
    {"id": 8, "owner": "Renee", "name": "Forgotten Heroes", "abbrev": "HERO"},
    {"id": 9, "owner": "Brett", "name": "Victorious Secret", "abbrev": "VS"},
    {"id": 10, "owner": "Omar", "name": "Average Joes", "abbrev": "JOE"},
]

# Hand-curated season records + season points (roughly correlate with roster
# strength below). wins + losses == 13 (weeks 1-13 complete).
SEASON_RECORDS: Dict[int, Dict[str, float]] = {
    1: {"wins": 9, "losses": 4},
    2: {"wins": 5, "losses": 8},
    3: {"wins": 10, "losses": 3},
    4: {"wins": 6, "losses": 7},
    5: {"wins": 8, "losses": 5},   # you
    6: {"wins": 7, "losses": 6},
    7: {"wins": 4, "losses": 9},
    8: {"wins": 6, "losses": 7},
    9: {"wins": 7, "losses": 6},
    10: {"wins": 3, "losses": 10},
}

# ----------------------------------------------------- player pool construction

NFL_TEAMS = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN",
    "DET", "GB", "HOU", "IND", "JAX", "KC", "LV", "LAC", "LAR", "MIA",
    "MIN", "NE", "NO", "NYG", "NYJ", "PHI", "PIT", "SF", "SEA", "TB",
    "TEN", "WAS",
]

# Real stars seeded at the top of each position so the draft board looks legit.
REAL_STARS = {
    "QB": ["Josh Allen", "Jalen Hurts", "Lamar Jackson", "Patrick Mahomes",
           "Joe Burrow", "Jayden Daniels", "C.J. Stroud", "Jordan Love"],
    "RB": ["Christian McCaffrey", "Bijan Robinson", "Breece Hall", "Saquon Barkley",
           "Jahmyr Gibbs", "Jonathan Taylor", "De'Von Achane", "Derrick Henry",
           "Josh Jacobs", "Kyren Williams", "Kenneth Walker III", "James Cook"],
    "WR": ["CeeDee Lamb", "Tyreek Hill", "Ja'Marr Chase", "Justin Jefferson",
           "Amon-Ra St. Brown", "A.J. Brown", "Puka Nacua", "Garrett Wilson",
           "Chris Olave", "Davante Adams", "Drake London", "DK Metcalf"],
    "TE": ["Sam LaPorta", "Travis Kelce", "Mark Andrews", "Trey McBride",
           "George Kittle", "Dalton Kincaid"],
    "K": ["Justin Tucker", "Harrison Butker", "Brandon Aubrey"],
    "DEF": ["49ers D/ST", "Cowboys D/ST", "Ravens D/ST", "Jets D/ST"],
}

FIRST_NAMES = [
    "Marcus", "Trey", "DeShawn", "Cole", "Jaylen", "Brandon", "Tyrell", "Quentin",
    "Isaiah", "Malik", "Brock", "Dante", "Xavier", "Cameron", "Drew", "Keenan",
    "Rashad", "Demarcus", "Tariq", "Donovan", "Elijah", "Bryce", "Carter", "Jamal",
    "Nico", "Reggie", "Tristan", "Devonta", "Amari", "Kendrick", "Hunter", "Gabe",
]
LAST_NAMES = [
    "Sanders", "Whitfield", "Greenlaw", "Castillo", "Beaumont", "Okafor", "Donnelly",
    "Vasquez", "Holloway", "Pruitt", "Langston", "Ferreira", "Maddox", "Calloway",
    "Tagovai", "Sinclair", "Rourke", "Bautista", "Ellison", "Kowalski", "Mensah",
    "Dubois", "Tran", "Abara", "Salazar", "Nakamura", "Friedman", "Okonkwo",
    "Delgado", "Petrov", "Hoffman", "Cisneros",
]

# Required pool sizes per position (10 teams need full lineups + bench depth).
POOL_SIZES = {"QB": 20, "RB": 40, "WR": 40, "TE": 20, "K": 10, "DEF": 12}

# Per-position base PPR season points: (top, bottom) linearly interpolated by rank.
POINTS_RANGE = {
    "QB": (385, 210),
    "RB": (345, 90),
    "WR": (335, 95),
    "TE": (240, 70),
    "K": (165, 110),
    "DEF": (175, 95),
}

# How much a position is valued on draft day (for ADP / search_rank ordering).
DRAFT_VALUE_MULT = {"QB": 0.78, "RB": 1.0, "WR": 0.97, "TE": 0.9, "K": 0.4, "DEF": 0.45}

BYE_WEEKS = [5, 6, 7, 9, 10, 11, 12, 13, 14]


def _gen_name(position: str, index: int, used: set) -> str:
    """Deterministically build a plausible unique player name."""
    f = FIRST_NAMES[(index * 7 + len(position)) % len(FIRST_NAMES)]
    for attempt in range(len(LAST_NAMES)):
        l = LAST_NAMES[(index * 5 + attempt + len(position) * 3) % len(LAST_NAMES)]
        name = f"{f} {l}"
        if name not in used:
            used.add(name)
            return name
    # Extremely unlikely fallback
    name = f"{f} {position}{index}"
    used.add(name)
    return name


def _build_pool() -> tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    """Construct (players_meta, projections, ordered_pool) for the whole league."""
    players: Dict[str, Any] = {}
    projections: Dict[str, Any] = {}
    ordered: List[Dict[str, Any]] = []
    used_names: set = set()
    pid_counter = 0

    for position, size in POOL_SIZES.items():
        top, bottom = POINTS_RANGE[position]
        stars = REAL_STARS.get(position, [])
        for rank in range(size):
            pid_counter += 1
            pid = f"p{pid_counter:04d}"
            if rank < len(stars):
                name = stars[rank]
                used_names.add(name)
            else:
                name = _gen_name(position, pid_counter, used_names)

            frac = rank / max(size - 1, 1)
            base_ppr = round(top - (top - bottom) * frac, 1)

            if position == "DEF":
                team = name.split(" ")[0][:3].upper()
                age = None
            else:
                team = NFL_TEAMS[(pid_counter * 3) % len(NFL_TEAMS)]
                age = 22 + (pid_counter % 12)

            meta = {
                "player_id": pid,
                "full_name": name,
                "first_name": name.split(" ")[0],
                "last_name": " ".join(name.split(" ")[1:]) or name,
                "position": position,
                "fantasy_positions": [position],
                "team": team,
                "bye_week": BYE_WEEKS[pid_counter % len(BYE_WEEKS)],
                "age": age,
                "injury_status": None,
                "_base_ppr": base_ppr,
                "_pos_rank": rank + 1,
            }
            players[pid] = meta
            ordered.append(meta)

            if position in ("QB", "K", "DEF"):
                half, std = base_ppr, base_ppr
            else:
                half = round(base_ppr * 0.93, 1)
                std = round(base_ppr * 0.86, 1)
            projections[pid] = {
                "pts_ppr": base_ppr,
                "pts_half_ppr": half,
                "pts_std": std,
            }

    # Assign ADP-style search_rank by overall draft value
    ordered.sort(key=lambda m: m["_base_ppr"] * DRAFT_VALUE_MULT[m["position"]], reverse=True)
    for i, meta in enumerate(ordered):
        meta["search_rank"] = i + 1
        players[meta["player_id"]]["search_rank"] = i + 1

    return players, projections, ordered


_PLAYERS, _PROJECTIONS, _ORDERED = _build_pool()


# ------------------------------------------------------------- roster allocation
# Give every team a full, realistic roster by drafting within each position in
# snake order so strength is spread fairly and quotas are guaranteed.
ROSTER_QUOTA = {"QB": 2, "RB": 4, "WR": 4, "TE": 2, "K": 1, "DEF": 1}  # 14 players
STARTER_PLAN = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF"]  # 9 starters


def _build_team_rosters() -> Dict[int, List[str]]:
    by_pos: Dict[str, List[str]] = {}
    for meta in sorted(_ORDERED, key=lambda m: m["_base_ppr"], reverse=True):
        by_pos.setdefault(meta["position"], []).append(meta["player_id"])

    team_ids = [t["id"] for t in TEAMS]
    rosters: Dict[int, List[str]] = {tid: [] for tid in team_ids}

    for position, count in ROSTER_QUOTA.items():
        pool = by_pos[position]
        idx = 0
        for draft_round in range(count):
            order = team_ids if draft_round % 2 == 0 else list(reversed(team_ids))
            for tid in order:
                if idx < len(pool):
                    rosters[tid].append(pool[idx])
                    idx += 1
    return rosters


_TEAM_ROSTERS = _build_team_rosters()


def _starters_and_bench(team_id: int) -> tuple[List[str], List[str]]:
    """Fixed starting lineup (by preseason strength) + bench for a team."""
    roster = list(_TEAM_ROSTERS[team_id])
    by_pos: Dict[str, List[str]] = {}
    for pid in roster:
        by_pos.setdefault(_PLAYERS[pid]["position"], []).append(pid)
    for pids in by_pos.values():
        pids.sort(key=lambda p: _PLAYERS[p]["_base_ppr"], reverse=True)

    starters: List[str] = []
    used: set = set()
    for slot in STARTER_PLAN:
        if slot == "FLEX":
            candidates = [
                p for pos in ("RB", "WR", "TE") for p in by_pos.get(pos, [])
                if p not in used
            ]
            candidates.sort(key=lambda p: _PLAYERS[p]["_base_ppr"], reverse=True)
            pick = candidates[0] if candidates else None
        else:
            pick = next((p for p in by_pos.get(slot, []) if p not in used), None)
        if pick:
            starters.append(pick)
            used.add(pick)
    bench = [p for p in roster if p not in used]
    return starters, bench


# --------------------------------------------------------- deterministic scoring


def _weekly_multiplier(player_id: str, week: int) -> float:
    """Stable per-player, per-week variance in [0.45, 1.6]."""
    h = 0
    for ch in f"{player_id}-{week}":
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return 0.45 + (h % 1000) / 1000.0 * 1.15


def _player_week_points(player_id: str, week: int) -> float:
    base_weekly = _PROJECTIONS[player_id]["pts_ppr"] / 17.0
    return round(base_weekly * _weekly_multiplier(player_id, week), 2)


def _team_week_lineup(team_id: int, week: int) -> Dict[str, Any]:
    starters, bench = _starters_and_bench(team_id)
    starter_records = [
        {"name": _PLAYERS[p]["full_name"], "points": _player_week_points(p, week)}
        for p in starters
    ]
    bench_records = [
        {"name": _PLAYERS[p]["full_name"], "points": _player_week_points(p, week)}
        for p in bench
    ]
    total = round(sum(r["points"] for r in starter_records), 2)
    return {"starters": starter_records, "bench": bench_records, "total": total}


def _week_schedule(week: int) -> List[tuple[int, int]]:
    """Round-robin pairings for the 10 teams, rotating by week."""
    ids = [t["id"] for t in TEAMS]
    n = len(ids)
    fixed = ids[0]
    rotating = ids[1:]
    r = (week - 1) % (n - 1)
    rotating = rotating[r:] + rotating[:r]
    arrangement = [fixed] + rotating
    pairs = []
    for i in range(n // 2):
        pairs.append((arrangement[i], arrangement[n - 1 - i]))
    return pairs


def _team_season_points(team_id: int) -> float:
    return round(
        sum(_team_week_lineup(team_id, w)["total"] for w in range(1, MOCK_CURRENT_WEEK)),
        2,
    )


# ============================================================ ESPN-shaped output


def espn_league_info() -> Dict[str, Any]:
    return {
        "id": MOCK_ESPN_LEAGUE_ID,
        "name": LEAGUE_NAME,
        "size": len(TEAMS),
        "current_week": MOCK_CURRENT_WEEK,
        "current_matchup_period": MOCK_CURRENT_WEEK,
        "is_active": True,
        "scoring_type": "ppr",
        "roster_settings": {
            "roster_size": 14,
            "position_limits": {},
            "lineup_slots": {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "K": 1, "D/ST": 1},
        },
        "scoring_settings": {"scoring_items": [], "player_rank_type": "PPR", "scoring_type": "H2H_POINTS"},
    }


def espn_teams() -> List[Dict[str, Any]]:
    out = []
    for t in TEAMS:
        rec = SEASON_RECORDS[t["id"]]
        out.append({
            "id": t["id"],
            "name": t["name"],
            "location": t["name"],
            "nickname": t["abbrev"],
            "abbreviation": t["abbrev"],
            "logo_url": "",
            "wins": rec["wins"],
            "losses": rec["losses"],
            "ties": 0,
            "points_for": _team_season_points(t["id"]),
            "points_against": round(_team_season_points(t["id"]) * 0.97, 2),
            "owners": [f"{{owner-{t['id']}}}"],
        })
    return out


def espn_weekly_player_points(week: int) -> Dict[int, Dict[str, Any]]:
    return {
        t["id"]: {
            k: v for k, v in _team_week_lineup(t["id"], week).items() if k != "total"
        }
        for t in TEAMS
    }


def espn_matchups(week: Optional[int]) -> List[Dict[str, Any]]:
    wk = week or (MOCK_CURRENT_WEEK - 1)
    pairs = _week_schedule(wk)
    matchups = []
    for i, (home_id, away_id) in enumerate(pairs, start=1):
        home = _team_week_lineup(home_id, wk)
        away = _team_week_lineup(away_id, wk)
        matchups.append({
            "matchup_id": i,
            "week": wk,
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_score": home["total"],
            "away_score": away["total"],
            "home_projected_score": round(home["total"] * 1.02, 2),
            "away_projected_score": round(away["total"] * 1.02, 2),
            "is_playoff": False,
            "winner": "HOME" if home["total"] >= away["total"] else "AWAY",
        })
    return matchups


def espn_team_roster(team_id: int, week: Optional[int]) -> Dict[str, Any]:
    wk = week or (MOCK_CURRENT_WEEK - 1)
    starters, bench = _starters_and_bench(team_id)
    roster = []
    for pid in starters + bench:
        meta = _PLAYERS[pid]
        is_bench = pid in bench
        roster.append({
            "player_id": pid,
            "full_name": meta["full_name"],
            "position_id": 0,
            "position_name": meta["position"],
            "lineup_slot_id": 20 if is_bench else 0,
            "lineup_slot_name": "BENCH" if is_bench else meta["position"],
            "pro_team_id": 0,
            "eligible_slots": [],
            "stats": {"actual": {}, "projected": {}},
            "applied_points": _player_week_points(pid, wk),
            "projected_points": _player_week_points(pid, wk),
        })
    return {"team_id": team_id, "roster": roster, "week": wk}


def espn_available_players(position: Optional[str] = None) -> List[Dict[str, Any]]:
    """Free agents: players in the pool not on any of the 10 rosters."""
    rostered = {pid for r in _TEAM_ROSTERS.values() for pid in r}
    out = []
    for meta in _ORDERED:
        if meta["player_id"] in rostered:
            continue
        if position and meta["position"] != position:
            continue
        out.append({
            "id": meta["player_id"],
            "espn_player_id": meta["player_id"],
            "full_name": meta["full_name"],
            "first_name": meta["first_name"],
            "last_name": meta["last_name"],
            "position_id": 0,
            "position_name": meta["position"],
            "pro_team_id": 0,
            "pro_team_abbr": meta["team"],
            "eligible_slots": [],
            "is_active": True,
            "injury_status": "ACTIVE",
            "stats": {},
            "season_points": meta["_base_ppr"],
            "last_week_points": 0.0,
            "average_points": round(meta["_base_ppr"] / 17.0, 2),
            "projected_points": meta["_base_ppr"],
            "ownership_percentage": 0.0,
            "latest_news": "",
            "news_updated": None,
        })
    out.sort(key=lambda p: p["projected_points"], reverse=True)
    return out


def espn_waiver_budgets() -> List[Dict[str, Any]]:
    budgets = []
    for t in TEAMS:
        spent = (t["id"] * 13) % 80
        budgets.append({
            "team_id": t["id"],
            "team_name": t["name"],
            "total_budget": 100.0,
            "spent_budget": float(spent),
            "current_budget": float(100 - spent),
        })
    return budgets


# ========================================================= Sleeper-shaped output


def _sleeper_users() -> List[Dict[str, Any]]:
    users = []
    for t in TEAMS:
        uid = MOCK_SLEEPER_USER_ID if t["id"] == 5 else f"bot_{t['id']}"
        users.append({
            "user_id": uid,
            "display_name": t["owner"],
            "metadata": {"team_name": t["name"]},
        })
    return users


def _sleeper_rosters() -> List[Dict[str, Any]]:
    rosters = []
    for t in TEAMS:
        uid = MOCK_SLEEPER_USER_ID if t["id"] == 5 else f"bot_{t['id']}"
        rec = SEASON_RECORDS[t["id"]]
        pf = _team_season_points(t["id"])
        rosters.append({
            "roster_id": t["id"],
            "owner_id": uid,
            "players": list(_TEAM_ROSTERS[t["id"]]),
            "starters": _starters_and_bench(t["id"])[0],
            "settings": {
                "wins": rec["wins"],
                "losses": rec["losses"],
                "ties": 0,
                "fpts": int(pf),
                "fpts_decimal": int(round((pf - int(pf)) * 100)),
            },
        })
    return rosters


def sleeper_rosters() -> List[Dict[str, Any]]:
    """Public alias used by the seed and the Sleeper mock responses."""
    return _sleeper_rosters()


def sleeper_league_users() -> List[Dict[str, Any]]:
    """Public alias used by the seed and the Sleeper mock responses."""
    return _sleeper_users()


def sleeper_league() -> Dict[str, Any]:
    return {
        "league_id": MOCK_SLEEPER_LEAGUE_ID,
        "name": LEAGUE_NAME,
        "season": str(MOCK_SEASON),
        "status": "in_season",
        "total_rosters": len(TEAMS),
        "scoring_settings": {},  # empty -> draft service uses precomputed pts_ppr
        "roster_positions": ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF",
                             "BN", "BN", "BN", "BN", "BN"],
        "settings": {"num_teams": len(TEAMS)},
    }


def sleeper_matchups(week: int) -> List[Dict[str, Any]]:
    pairs = _week_schedule(week)
    matchup_of: Dict[int, int] = {}
    for mid, (a, b) in enumerate(pairs, start=1):
        matchup_of[a] = mid
        matchup_of[b] = mid

    out = []
    for t in TEAMS:
        tid = t["id"]
        starters, bench = _starters_and_bench(tid)
        players_points = {
            pid: _player_week_points(pid, week) for pid in starters + bench
        }
        total = round(sum(players_points[p] for p in starters), 2)
        out.append({
            "roster_id": tid,
            "matchup_id": matchup_of[tid],
            "points": total,
            "starters": starters,
            "players": starters + bench,
            "players_points": players_points,
        })
    return out


def sleeper_drafts() -> List[Dict[str, Any]]:
    return [{
        "draft_id": MOCK_SLEEPER_DRAFT_ID,
        "league_id": MOCK_SLEEPER_LEAGUE_ID,
        "status": "drafting",
        "type": "snake",
        "season": str(MOCK_SEASON),
        "settings": {"teams": len(TEAMS), "rounds": 14},
    }]


def _draft_order() -> Dict[str, int]:
    order = {}
    for t in TEAMS:
        uid = MOCK_SLEEPER_USER_ID if t["id"] == 5 else f"bot_{t['id']}"
        order[uid] = t["id"]  # slot == team id
    return order


def sleeper_draft() -> Dict[str, Any]:
    return {
        "draft_id": MOCK_SLEEPER_DRAFT_ID,
        "league_id": MOCK_SLEEPER_LEAGUE_ID,
        "status": "drafting",
        "type": "snake",
        "season": str(MOCK_SEASON),
        "settings": {"teams": len(TEAMS), "rounds": 14},
        "draft_order": _draft_order(),
        "slot_to_roster_id": {str(t["id"]): t["id"] for t in TEAMS},
        "metadata": {"roster_positions": sleeper_league()["roster_positions"]},
    }


# An in-progress snake draft: the first ~2.4 rounds are done, so the demo Draft
# Room shows real picks AND live best-available recommendations.
MOCK_PICKS_MADE = 24


def sleeper_draft_picks() -> List[Dict[str, Any]]:
    team_count = len(TEAMS)
    board = sorted(_ORDERED, key=lambda m: m["search_rank"])
    picks = []
    for overall in range(1, MOCK_PICKS_MADE + 1):
        rnd = (overall - 1) // team_count + 1
        pos_in_round = (overall - 1) % team_count
        slot = pos_in_round + 1 if rnd % 2 == 1 else team_count - pos_in_round
        uid = MOCK_SLEEPER_USER_ID if slot == 5 else f"bot_{slot}"
        meta = board[overall - 1]
        picks.append({
            "pick_no": overall,
            "round": rnd,
            "roster_id": slot,
            "picked_by": uid,
            "player_id": meta["player_id"],
            "metadata": {
                "first_name": meta["first_name"],
                "last_name": meta["last_name"],
                "position": meta["position"],
                "team": meta["team"],
            },
        })
    return picks


def sleeper_all_players() -> Dict[str, Any]:
    out = {}
    for pid, meta in _PLAYERS.items():
        out[pid] = {
            "player_id": pid,
            "full_name": meta["full_name"],
            "first_name": meta["first_name"],
            "last_name": meta["last_name"],
            "position": meta["position"],
            "fantasy_positions": meta["fantasy_positions"],
            "team": meta["team"],
            "bye_week": meta["bye_week"],
            "age": meta["age"],
            "injury_status": meta["injury_status"],
            "search_rank": meta["search_rank"],
        }
    return out


def sleeper_projections(season: int) -> Dict[str, Any]:
    return {pid: dict(proj) for pid, proj in _PROJECTIONS.items()}


def sleeper_user(identifier: str) -> Dict[str, Any]:
    return {
        "user_id": MOCK_SLEEPER_USER_ID,
        "username": "demo_manager",
        "display_name": DEMO_USER_NAME,
        "avatar": None,
    }


def sleeper_user_leagues(user_id: str, season: int) -> List[Dict[str, Any]]:
    return [sleeper_league()]


# ----------------------------------------------------------- content profile seed

def seed_personas() -> List[Dict[str, Any]]:
    """Personas auto-filled from the fixture league's owners + team names."""
    bits = {
        1: ["drafts a kicker too early every year", "won't stop talking about 2019"],
        2: ["perpetual bench points leader", "starts injured players on bye"],
        3: ["trade machine addict", "names every player his 'guy'"],
        4: ["streams defenses religiously", "claims he's rebuilding"],
        5: ["the eternal optimist", "comeback specialist"],
        6: ["all offense no defense", "rage-drops after one bad week"],
        7: ["meme lord of the group chat", "all-in on rookies"],
        8: ["quiet until playoffs", "hoards waiver budget"],
        9: ["smack-talk champion", "never reads the matchup"],
        10: ["middle of the pack forever", "forgets to set his lineup"],
    }
    personas = []
    for t in TEAMS:
        personas.append({
            "name": t["owner"],
            "team_name": t["name"],
            "notes": f"Manager of {t['name']}.",
            "bits": bits.get(t["id"], []),
        })
    return personas


def espn_team_owner_pairs() -> List[Dict[str, str]]:
    """[{team_name, owner_name}] for the mock league (auto-fill personas)."""
    return [{"team_name": t["name"], "owner_name": t["owner"]} for t in TEAMS]


def seed_voice_guide() -> str:
    return (
        "We are a 10-team league of college friends who have played together for "
        "years. The tone is brutal, sarcastic, and deeply personal: roast the "
        "losers by name, reference old blowups and running jokes, and never sound "
        "like a corporate recap. Short punchy sentences, a little profanity-adjacent "
        "snark, and zero participation trophies."
    )


def seed_humor_examples() -> List[Dict[str, Any]]:
    return [{
        "title": "Week 12 sample",
        "year": MOCK_SEASON,
        "text": (
            "Another week, another reminder that Kev drafts like he's allergic to "
            "winning. Show Me Your TDs put up a cool 71 points and somehow that "
            "wasn't even the most embarrassing thing to happen in the group chat. "
            "Meanwhile Victorious Secret keeps talking trash he can't back up, and "
            "the Average Joes once again proved the name is doing a lot of heavy "
            "lifting. See you all next week, losers."
        ),
    }]
