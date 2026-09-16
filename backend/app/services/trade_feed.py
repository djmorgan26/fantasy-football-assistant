"""Reading trades *out of* the platforms, in one shape.

The app could not previously see a trade at all: the analyzer only understood
trades you typed in yourself, by ESPN player id. This module is the other half,
the offers that already exist, pending and historical, pulled from whichever
platform the league lives on and flattened into a single `NormalizedTrade` so
the API and the UI never branch on platform.

What each platform will tell us differs, and the difference is not cosmetic:

| | pending offers | completed history | auth |
| --- | --- | --- | --- |
| ESPN | yes, `mPendingTransactions` | yes, `mTransactions2` | public leagues need none |
| Sleeper | **only via GraphQL** | yes, `/transactions/{week}` | pending needs a user token |

Sleeper's public v1 API returns completed transactions only. A trade sitting in
your inbox is simply absent from it, which is why this is worth the extra path.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import structlog

from app.core.config import settings
from app.models.league import League, PlatformType
from app.models.team import Team
from app.services.espn_service import ESPNCookies, ESPNError, ESPNService
from app.services import mock_data
from app.services.sleeper_service import SleeperError, SleeperService

logger = structlog.get_logger()

# How many past weeks of Sleeper transactions to scan for completed trades.
# Far enough back to be a useful history, short enough not to be 17 requests.
SLEEPER_HISTORY_WEEKS = 6

# ESPN encodes what a transaction item does to a player as an integer.
_ESPN_TRADE_ITEM_TYPES = {178: "TRADE"}


@dataclass
class TradeParty:
    """One team's side of a trade."""

    team_id: Optional[int]
    team_name: str
    platform_team_id: Optional[Any] = None
    sends: List[Dict[str, Any]] = field(default_factory=list)
    has_consented: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "platform_team_id": self.platform_team_id,
            "sends": self.sends,
            "has_consented": self.has_consented,
        }


@dataclass
class NormalizedTrade:
    """A trade from any platform, in the one shape the app renders."""

    trade_id: str
    status: str  # proposed | accepted | rejected | executed | vetoed
    direction: str  # incoming | outgoing | other
    parties: List[TradeParty]
    proposed_at: Optional[str] = None
    week: Optional[int] = None
    source: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "status": self.status,
            "direction": self.direction,
            "parties": [p.to_dict() for p in self.parties],
            "proposed_at": self.proposed_at,
            "week": self.week,
            "source": self.source,
        }


def _epoch_ms_to_iso(value: Any) -> Optional[str]:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _brief(player: Dict[str, Any]) -> Dict[str, Any]:
    """The player fields a trade card needs, and nothing else."""
    from app.services.trade_engine import normalize_position, player_points

    return {
        "player_id": str(player.get("player_id")),
        "full_name": player.get("full_name") or str(player.get("player_id")),
        "position": normalize_position(player.get("position_name")),
        "pro_team": player.get("pro_team_abbr"),
        "projected_points": round(player_points(player), 2),
        "injury_status": player.get("injury_status"),
    }


async def fetch_trades(
    league: League,
    teams: Sequence[Team],
    my_team: Optional[Team],
    rosters: Dict[int, List[Dict[str, Any]]],
    cookies: Optional[ESPNCookies] = None,
    sleeper_token: Optional[str] = None,
) -> List[NormalizedTrade]:
    """Every trade this league will show us, pending first.

    `rosters` is a team-id-keyed map of already-loaded rosters, used to put a
    name and a projection on a bare player id. A player who has already changed
    hands will not be on the roster the trade moved him from, so anything not
    found falls back to the platform's own player index rather than rendering a
    numeric id at the user.

    Never raises: a platform that will not answer yields an empty list, because
    an Offers tab that shows nothing is a far better failure than a page that
    will not load.
    """
    try:
        if league.platform == PlatformType.SLEEPER and league.sleeper_league_id:
            return await _sleeper_trades(
                league, teams, my_team, rosters, sleeper_token
            )
        if league.espn_league_id:
            return await _espn_trades(league, teams, my_team, rosters, cookies)
    except (ESPNError, SleeperError) as e:
        logger.warning("Trade feed unavailable", league_id=league.id, error=str(e))
    except Exception as e:  # noqa: BLE001 - one bad feed must not break the page
        logger.warning(
            "Trade feed failed unexpectedly", league_id=league.id, error=str(e)
        )
    return []


# ---------------------------------------------------------------------------
# Sleeper
# ---------------------------------------------------------------------------


async def _sleeper_trades(
    league: League,
    teams: Sequence[Team],
    my_team: Optional[Team],
    rosters: Dict[int, List[Dict[str, Any]]],
    token: Optional[str],
) -> List[NormalizedTrade]:
    service = SleeperService()
    by_roster = {t.sleeper_roster_id: t for t in teams if t.sleeper_roster_id is not None}
    my_roster_id = my_team.sleeper_roster_id if my_team else None

    # Names for players who have already moved and so are on nobody's roster
    # in our snapshot.
    from app.services.draft_service import draft_service

    try:
        players_index = await draft_service.get_players_cached()
    except Exception as e:  # noqa: BLE001
        logger.warning("Sleeper player index unavailable", error=str(e))
        players_index = {}

    lookup = _roster_lookup(rosters)

    def resolve(player_id: Any) -> Dict[str, Any]:
        found = lookup.get(str(player_id))
        if found:
            return _brief(found)
        meta = players_index.get(str(player_id)) or {}
        name = meta.get("full_name") or (
            f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip()
        )
        return {
            "player_id": str(player_id),
            "full_name": name or str(player_id),
            "position": meta.get("position") or "UNKNOWN",
            "pro_team": meta.get("team"),
            "projected_points": 0.0,
            "injury_status": meta.get("injury_status"),
        }

    raw: List[Dict[str, Any]] = []

    if token:
        raw.extend(await service.get_proposed_trades(league.sleeper_league_id, token))

    current_week = int(league.current_week or 1)
    weeks = [w for w in range(current_week, max(current_week - SLEEPER_HISTORY_WEEKS, 0), -1)]

    async def week_trades(week: int) -> List[Dict[str, Any]]:
        try:
            rows = await service.get_transactions(league.sleeper_league_id, week)
        except SleeperError as e:
            logger.warning("Sleeper transactions unavailable", week=week, error=str(e))
            return []
        return [r for r in rows or [] if r.get("type") == "trade"]

    for batch in await asyncio.gather(*(week_trades(w) for w in weeks)):
        raw.extend(batch)

    trades: List[NormalizedTrade] = []
    seen: set = set()
    for row in raw:
        trade_id = str(row.get("transaction_id") or "")
        if not trade_id or trade_id in seen:
            continue
        seen.add(trade_id)

        # `adds` maps player id -> the roster receiving him, so a party's
        # outgoing players are the adds pointing at *other* rosters.
        adds = row.get("adds") or {}
        roster_ids = row.get("roster_ids") or []
        consenters = set(row.get("consenter_ids") or [])

        parties: List[TradeParty] = []
        for roster_id in roster_ids:
            team = by_roster.get(roster_id)
            sends = [
                resolve(pid)
                for pid, destination in adds.items()
                if destination != roster_id
                and (row.get("drops") or {}).get(pid) == roster_id
            ]
            parties.append(
                TradeParty(
                    team_id=team.id if team else None,
                    team_name=team.name if team else f"Roster {roster_id}",
                    platform_team_id=roster_id,
                    sends=sends,
                    has_consented=roster_id in consenters,
                )
            )

        status = "proposed" if row.get("status") == "proposed" else "executed"
        if row.get("status") in ("vetoed", "failed"):
            status = "vetoed"

        trades.append(
            NormalizedTrade(
                trade_id=trade_id,
                status=status,
                direction=_direction(status, my_roster_id, roster_ids, consenters),
                parties=parties,
                proposed_at=_epoch_ms_to_iso(row.get("created")),
                week=row.get("leg"),
                source="sleeper",
            )
        )

    return _sorted(trades)


def _direction(
    status: str,
    my_platform_id: Optional[Any],
    involved: Sequence[Any],
    consenters: set,
) -> str:
    """Whether an offer is one I received, one I sent, or none of my business.

    A proposed trade lists everyone who has agreed so far, and the proposer is
    always among them. So if I am in the trade but not in `consenter_ids`, I am
    the one being asked: the offer is incoming.
    """
    if my_platform_id is None or my_platform_id not in involved:
        return "other"
    if status != "proposed":
        return "other"
    return "outgoing" if my_platform_id in consenters else "incoming"


def _roster_lookup(rosters: Dict[int, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for entries in rosters.values():
        for player in entries:
            lookup[str(player.get("player_id"))] = player
    return lookup


# ---------------------------------------------------------------------------
# ESPN
# ---------------------------------------------------------------------------


async def _espn_trades(
    league: League,
    teams: Sequence[Team],
    my_team: Optional[Team],
    rosters: Dict[int, List[Dict[str, Any]]],
    cookies: Optional[ESPNCookies],
) -> List[NormalizedTrade]:
    service = ESPNService()
    by_espn_id = {t.espn_team_id: t for t in teams if t.espn_team_id is not None}
    my_espn_id = my_team.espn_team_id if my_team else None
    lookup = _roster_lookup(rosters)

    async def view(name: str) -> Dict[str, Any]:
        try:
            return await service._make_request(
                str(league.espn_league_id), cookies=cookies, params={"view": name}
            )
        except ESPNError as e:
            logger.warning("ESPN trade view unavailable", view=name, error=str(e))
            return {}
        except Exception as e:  # noqa: BLE001 - an HTTP error is not a page error
            logger.warning("ESPN trade view failed", view=name, error=str(e))
            return {}

    # `_make_request` is the raw transport and does not short-circuit in mock
    # mode the way the higher-level ESPNService methods do.
    if settings.mock_mode:
        pending_data, history_data = mock_data.espn_trade_views()
    else:
        pending_data, history_data = await asyncio.gather(
            view("mPendingTransactions"), view("mTransactions2")
        )

    raw = list(pending_data.get("pendingTransactions") or [])
    raw.extend(history_data.get("transactions") or [])

    trades: List[NormalizedTrade] = []
    seen: set = set()
    for row in raw:
        if str(row.get("type") or "").upper() not in ("TRADE_PROPOSAL", "TRADE", "TRADE_ACCEPT"):
            continue
        trade_id = str(row.get("id") or "")
        if not trade_id or trade_id in seen:
            continue
        seen.add(trade_id)

        # ESPN items carry fromTeamId / toTeamId per player.
        sends_by_team: Dict[int, List[Dict[str, Any]]] = {}
        for item in row.get("items") or []:
            from_team = item.get("fromTeamId")
            player_id = item.get("playerId")
            if from_team is None or player_id is None:
                continue
            found = lookup.get(str(player_id))
            sends_by_team.setdefault(from_team, []).append(
                _brief(found) if found else {
                    "player_id": str(player_id),
                    "full_name": f"Player {player_id}",
                    "position": "UNKNOWN",
                    "pro_team": None,
                    "projected_points": 0.0,
                    "injury_status": None,
                }
            )

        involved = sorted(sends_by_team.keys())
        if not involved:
            continue

        status_raw = str(row.get("status") or "").upper()
        status = {
            "PENDING": "proposed",
            "EXECUTED": "executed",
            "ACCEPTED": "executed",
            "REJECTED": "rejected",
            "VETOED": "vetoed",
        }.get(status_raw, "executed")

        # ESPN marks the proposing team on the transaction itself.
        proposer = row.get("teamId")
        consenters = {proposer} if proposer is not None else set()

        parties = [
            TradeParty(
                team_id=by_espn_id[tid].id if tid in by_espn_id else None,
                team_name=by_espn_id[tid].name if tid in by_espn_id else f"Team {tid}",
                platform_team_id=tid,
                sends=sends_by_team.get(tid, []),
                has_consented=tid in consenters,
            )
            for tid in involved
        ]

        trades.append(
            NormalizedTrade(
                trade_id=trade_id,
                status=status,
                direction=_direction(status, my_espn_id, involved, consenters),
                parties=parties,
                proposed_at=_epoch_ms_to_iso(row.get("proposedDate")),
                week=row.get("scoringPeriodId"),
                source="espn",
            )
        )

    return _sorted(trades)


def _sorted(trades: List[NormalizedTrade]) -> List[NormalizedTrade]:
    """Pending first, then newest. An offer needing an answer outranks history."""
    rank = {"proposed": 0, "executed": 1, "rejected": 2, "vetoed": 3}
    return sorted(
        trades,
        key=lambda t: (rank.get(t.status, 4), -(_sort_time(t.proposed_at))),
    )


def _sort_time(value: Optional[str]) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Remaining schedule
# ---------------------------------------------------------------------------


async def remaining_schedule(
    league: League,
    teams: Sequence[Team],
    from_week: int,
    through_week: int,
    cookies: Optional[ESPNCookies] = None,
) -> List[List[tuple]]:
    """The games still to be played, as (team_id, team_id) pairs per week.

    Worth the extra requests. Simulating the rest of the season against random
    pairings makes every team's odds a function of strength alone, which washes
    out exactly the thing a manager cares about: that they still have to play
    the two best teams in the league. Both platforms publish the full schedule
    up front, so the simulation can use the real one.

    Returns [] when neither platform will say, and the caller falls back to a
    strength-only estimate rather than inventing a schedule.
    """
    if through_week < from_week:
        return []

    try:
        if league.platform == PlatformType.SLEEPER and league.sleeper_league_id:
            return await _sleeper_schedule(league, teams, from_week, through_week)
        if league.espn_league_id:
            return await _espn_schedule(league, teams, from_week, through_week, cookies)
    except (ESPNError, SleeperError) as e:
        logger.warning("Schedule unavailable", league_id=league.id, error=str(e))
    except Exception as e:  # noqa: BLE001
        logger.warning("Schedule failed unexpectedly", league_id=league.id, error=str(e))
    return []


async def _sleeper_schedule(
    league: League, teams: Sequence[Team], from_week: int, through_week: int
) -> List[List[tuple]]:
    """Sleeper publishes future weeks as matchup rows with no scores yet.

    Two rows sharing a `matchup_id` are the pairing; Sleeper has no notion of
    home and away, so the order within a pair is arbitrary and irrelevant to the
    simulation.
    """
    service = SleeperService()
    by_roster = {t.sleeper_roster_id: t.id for t in teams if t.sleeper_roster_id is not None}

    async def week(number: int) -> List[tuple]:
        try:
            rows = await service.get_matchups(league.sleeper_league_id, number)
        except SleeperError:
            return []
        pairs: Dict[Any, List[int]] = {}
        for row in rows or []:
            matchup_id = row.get("matchup_id")
            team_id = by_roster.get(row.get("roster_id"))
            if matchup_id is None or team_id is None:
                continue
            pairs.setdefault(matchup_id, []).append(team_id)
        return [(a, b) for a, b in (p for p in pairs.values() if len(p) == 2)]

    weeks = range(from_week, through_week + 1)
    return [w for w in await asyncio.gather(*(week(n) for n in weeks)) if w]


async def _espn_schedule(
    league: League,
    teams: Sequence[Team],
    from_week: int,
    through_week: int,
    cookies: Optional[ESPNCookies],
) -> List[List[tuple]]:
    """ESPN returns the whole season's schedule in one `mMatchup` response.

    Deliberately not `ESPNService.get_matchups`: that also fetches every team's
    projected lineup for the week, which is a lot of work to throw away when all
    we want is who plays whom.
    """
    service = ESPNService()
    by_espn = {t.espn_team_id: t.id for t in teams if t.espn_team_id is not None}

    # `_make_request` is the raw transport: unlike ESPNService's public methods
    # it has no mock-mode branch, so without this the test suite would reach the
    # real ESPN API.
    if settings.mock_mode:
        weeks_out: List[List[tuple]] = []
        for number in range(from_week, through_week + 1):
            games = [
                (by_espn.get(g["home_team_id"]), by_espn.get(g["away_team_id"]))
                for g in mock_data.espn_matchups(number)
            ]
            pairs = [(h, a) for h, a in games if h is not None and a is not None]
            if pairs:
                weeks_out.append(pairs)
        return weeks_out

    data = await service._make_request(
        str(league.espn_league_id), cookies=cookies, params={"view": "mMatchup"}
    )

    weeks: Dict[int, List[tuple]] = {}
    for game in data.get("schedule") or []:
        period = game.get("matchupPeriodId")
        if not isinstance(period, int) or not (from_week <= period <= through_week):
            continue
        home = by_espn.get((game.get("home") or {}).get("teamId"))
        away = by_espn.get((game.get("away") or {}).get("teamId"))
        if home is None or away is None:
            continue  # a bye, or a team we have not synced
        weeks.setdefault(period, []).append((home, away))

    return [weeks[w] for w in sorted(weeks)]
