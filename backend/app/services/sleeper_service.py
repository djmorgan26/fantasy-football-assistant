"""
Sleeper Fantasy Football API Service
Provides async interface to Sleeper API endpoints
API Documentation: https://docs.sleeper.app/
"""
import asyncio
import time

import httpx
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import structlog

from app.core.config import settings
from app.services import mock_data

logger = structlog.get_logger()

# Sleeper publishes a season-long projection rather than a weekly one, so a
# per-week number has to be prorated across the regular season.
REGULAR_SEASON_WEEKS = 17


class SleeperError(Exception):
    """Base exception for Sleeper API errors"""
    pass


class SleeperConnectionError(SleeperError):
    """Exception for connection errors"""
    pass


class SleeperNotFoundError(SleeperError):
    """Exception for 404 errors"""
    pass


# Sleeper's reads are public GETs of slowly-changing data, and the app fans out
# hard over them: building the league-wide ownership map asks for a roster per
# team, so one /api/news/league request used to pull the same league, rosters
# and matchups a dozen times each. A short TTL collapses that fan-out into one
# call without making anything meaningfully staler - Game Day already refetches
# on a two-minute timer.
_REQUEST_TTL_SECONDS = 30.0
_request_cache: Dict[str, Tuple[float, Any]] = {}
_request_locks: Dict[str, Tuple[Any, asyncio.Lock]] = {}


def _request_lock(key: str) -> asyncio.Lock:
    """A lock per endpoint, rebuilt whenever the event loop changes.

    These live at module scope, so a reused serverless container can hand them
    a fresh loop; a lock left over from a dead one raises rather than waits.
    """
    loop = asyncio.get_running_loop()
    existing = _request_locks.get(key)
    if existing is None or existing[0] is not loop:
        lock = asyncio.Lock()
        _request_locks[key] = (loop, lock)
        return lock
    return existing[1]


def _cached_response(key: str) -> Optional[Tuple[Any]]:
    """The cached value wrapped in a tuple, or None. A bare None is a value."""
    hit = _request_cache.get(key)
    if hit is None:
        return None
    cached_at, value = hit
    if time.monotonic() - cached_at >= _REQUEST_TTL_SECONDS:
        return None
    return (value,)


def clear_request_cache() -> None:
    """Drop everything. Used between tests, where mock and real must not mix."""
    _request_cache.clear()
    _request_locks.clear()


class SleeperService:
    """
    Service for interacting with Sleeper Fantasy Football API

    No authentication required - all endpoints are public read-only.
    Rate limit: Stay under 1000 requests per minute to avoid IP blocking.
    """

    def __init__(self):
        self.base_url = "https://api.sleeper.app/v1"
        self.timeout = httpx.Timeout(30.0)
        self.sport = "nfl"  # Sleeper supports multiple sports

        # Position mappings (Sleeper uses standard abbreviations)
        self.position_map = {
            "QB": "QB",
            "RB": "RB",
            "WR": "WR",
            "TE": "TE",
            "K": "K",
            "DEF": "D/ST",
            "FLEX": "FLEX",
            "SUPER_FLEX": "SFLEX",
            "BN": "BENCH",
            "IR": "IR"
        }

    async def _make_request(self, endpoint: str, max_retries: int = 3) -> Any:
        """Cached, single-flight wrapper around the real fetch."""
        hit = _cached_response(endpoint)
        if hit is not None:
            return hit[0]

        async with _request_lock(endpoint):
            # The holder of the lock has almost certainly just filled this.
            hit = _cached_response(endpoint)
            if hit is not None:
                return hit[0]

            value = await self._fetch(endpoint, max_retries)
            # Only successes are cached; a raise propagates and is retried next
            # time rather than being remembered as an answer.
            _request_cache[endpoint] = (time.monotonic(), value)
            return value

    async def _fetch(
        self,
        endpoint: str,
        max_retries: int = 3
    ) -> Any:
        """
        Make async HTTP request to Sleeper API

        Args:
            endpoint: API endpoint (without base URL)
            max_retries: Number of retry attempts

        Returns:
            Parsed JSON response

        Raises:
            SleeperConnectionError: For connection issues
            SleeperNotFoundError: For 404 errors
            SleeperError: For other API errors
        """
        # Mock mode: serve realistic sample data, no network call.
        if settings.mock_mode:
            return self._mock_response(endpoint)

        url = f"{self.base_url}/{endpoint}"

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; FantasyFootballAssistant/1.0)",
            "Accept": "application/json"
        }

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, headers=headers)

                    if response.status_code == 200:
                        logger.info("Sleeper API request successful", url=url, attempt=attempt + 1)
                        return response.json()

                    elif response.status_code == 404:
                        logger.warning("Sleeper resource not found", url=url, status=404)
                        raise SleeperNotFoundError(f"Resource not found: {endpoint}")

                    elif response.status_code == 429:
                        logger.warning("Sleeper rate limit hit", url=url, attempt=attempt + 1)
                        if attempt < max_retries - 1:
                            await httpx.AsyncClient().aclose()
                            continue
                        raise SleeperError("Rate limit exceeded. Please try again later.")

                    else:
                        logger.error("Sleeper API error", url=url, status=response.status_code)
                        raise SleeperError(f"API error: {response.status_code}")

            except httpx.TimeoutException:
                logger.warning("Sleeper API timeout", url=url, attempt=attempt + 1)
                if attempt < max_retries - 1:
                    continue
                raise SleeperConnectionError("Request timed out")

            except httpx.RequestError as e:
                logger.error("Sleeper request error", url=url, error=str(e), attempt=attempt + 1)
                if attempt < max_retries - 1:
                    continue
                raise SleeperConnectionError(f"Connection error: {str(e)}")

        raise SleeperConnectionError("Max retries exceeded")

    def _mock_response(self, endpoint: str) -> Any:
        """Route a Sleeper endpoint to deterministic mock data (MOCK_MODE)."""
        path = endpoint.split("?", 1)[0].strip("/")
        parts = path.split("/")

        # state/nfl
        if parts[:2] == ["state", "nfl"]:
            return {
                "week": mock_data.MOCK_CURRENT_WEEK,
                "leg": mock_data.MOCK_CURRENT_WEEK,
                "season": str(mock_data.MOCK_SEASON),
                "season_type": "regular",
                "display_week": mock_data.MOCK_CURRENT_WEEK,
            }

        # players/nfl, players/nfl/trending/<type>
        if parts[:2] == ["players", "nfl"]:
            if len(parts) >= 3 and parts[2] == "trending":
                return []
            return mock_data.sleeper_all_players()

        # projections/nfl/regular/<season>[/<week>]
        if parts[:1] == ["projections"]:
            season = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else mock_data.MOCK_SEASON
            return mock_data.sleeper_projections(season)

        # stats/nfl/...
        if parts[:1] == ["stats"]:
            return {}

        # user/<id>, user/<id>/leagues/nfl/<season>
        if parts[:1] == ["user"]:
            if "leagues" in parts:
                season = int(parts[-1]) if parts[-1].isdigit() else mock_data.MOCK_SEASON
                return mock_data.sleeper_user_leagues(parts[1], season)
            return mock_data.sleeper_user(parts[1] if len(parts) > 1 else "")

        # draft/<id>, draft/<id>/picks, draft/<id>/traded_picks
        if parts[:1] == ["draft"]:
            if parts[-1] == "picks":
                return mock_data.sleeper_draft_picks()
            if parts[-1] == "traded_picks":
                return []
            return mock_data.sleeper_draft()

        # league/<id>/...
        if parts[:1] == ["league"]:
            if len(parts) == 2:
                return mock_data.sleeper_league()
            tail = parts[2]
            if tail == "rosters":
                return mock_data.sleeper_rosters()
            if tail == "users":
                return mock_data.sleeper_league_users()
            if tail == "matchups":
                week = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else mock_data.MOCK_CURRENT_WEEK - 1
                return mock_data.sleeper_matchups(week)
            if tail == "drafts":
                return mock_data.sleeper_drafts()
            if tail == "transactions":
                week = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else mock_data.MOCK_CURRENT_WEEK
                return mock_data.sleeper_transactions(week)
            if tail in ("traded_picks", "winners_bracket", "losers_bracket"):
                return []
            return mock_data.sleeper_league()

        logger.warning("Unmapped mock Sleeper endpoint", endpoint=endpoint)
        return {}

    # ==================== USER ENDPOINTS ====================

    async def get_nfl_state(self) -> Dict[str, Any]:
        """The current NFL week and season, as Sleeper sees it.

        Authoritative and free. A league's own `settings.leg` is only correct
        until the next kickoff, so anything captured at connect time drifts for
        the rest of the season.
        """
        return await self._make_request("state/nfl")

    async def get_user(self, user_identifier: str) -> Dict[str, Any]:
        """
        Get user information by username or user ID

        Args:
            user_identifier: Username or user_id

        Returns:
            User data including user_id, username, display_name, avatar
        """
        endpoint = f"user/{user_identifier}"
        return await self._make_request(endpoint)

    async def get_user_leagues(self, user_id: str, season: int) -> List[Dict[str, Any]]:
        """
        Get all leagues for a user in a specific season

        Args:
            user_id: Sleeper user ID
            season: Year (e.g., 2024, 2025)

        Returns:
            List of league data
        """
        endpoint = f"user/{user_id}/leagues/{self.sport}/{season}"
        return await self._make_request(endpoint)

    # ==================== LEAGUE ENDPOINTS ====================

    async def get_league(self, league_id: str) -> Dict[str, Any]:
        """
        Get league information

        Args:
            league_id: Sleeper league ID

        Returns:
            League data including settings, scoring, roster positions
        """
        endpoint = f"league/{league_id}"
        return await self._make_request(endpoint)

    async def get_rosters(self, league_id: str) -> List[Dict[str, Any]]:
        """
        Get all rosters in a league

        Args:
            league_id: Sleeper league ID

        Returns:
            List of roster data with players, settings, wins/losses
        """
        endpoint = f"league/{league_id}/rosters"
        return await self._make_request(endpoint)

    async def get_league_users(self, league_id: str) -> List[Dict[str, Any]]:
        """
        Get all users in a league

        Args:
            league_id: Sleeper league ID

        Returns:
            List of user data
        """
        endpoint = f"league/{league_id}/users"
        return await self._make_request(endpoint)

    async def get_matchups(self, league_id: str, week: int) -> List[Dict[str, Any]]:
        """
        Get all matchups for a specific week

        Args:
            league_id: Sleeper league ID
            week: Week number (1-18 for regular season)

        Returns:
            List of matchup data with scores and rosters
        """
        endpoint = f"league/{league_id}/matchups/{week}"
        return await self._make_request(endpoint)

    async def get_transactions(self, league_id: str, week: int) -> List[Dict[str, Any]]:
        """
        Get all transactions for a specific week

        Args:
            league_id: Sleeper league ID
            week: Week number

        Returns:
            List of transaction data (adds, drops, trades)
        """
        endpoint = f"league/{league_id}/transactions/{week}"
        return await self._make_request(endpoint)

    async def get_traded_picks(self, league_id: str) -> List[Dict[str, Any]]:
        """
        Get all traded draft picks in a league

        Args:
            league_id: Sleeper league ID

        Returns:
            List of traded pick data
        """
        endpoint = f"league/{league_id}/traded_picks"
        return await self._make_request(endpoint)

    async def get_winning_bracket(self, league_id: str) -> List[Dict[str, Any]]:
        """
        Get winners playoff bracket

        Args:
            league_id: Sleeper league ID

        Returns:
            Playoff bracket data
        """
        endpoint = f"league/{league_id}/winners_bracket"
        return await self._make_request(endpoint)

    async def get_losing_bracket(self, league_id: str) -> List[Dict[str, Any]]:
        """
        Get losers playoff bracket

        Args:
            league_id: Sleeper league ID

        Returns:
            Playoff bracket data
        """
        endpoint = f"league/{league_id}/losers_bracket"
        return await self._make_request(endpoint)

    # ==================== DRAFT ENDPOINTS ====================

    async def get_league_drafts(self, league_id: str) -> List[Dict[str, Any]]:
        """
        Get all drafts for a league (a league can have multiple over seasons)

        Args:
            league_id: Sleeper league ID

        Returns:
            List of draft summaries (most recent first)
        """
        endpoint = f"league/{league_id}/drafts"
        return await self._make_request(endpoint)

    async def get_draft(self, draft_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a single draft

        Args:
            draft_id: Sleeper draft ID

        Returns:
            Draft data including status, type, settings, draft_order,
            slot_to_roster_id mapping, and start time
        """
        endpoint = f"draft/{draft_id}"
        return await self._make_request(endpoint)

    async def get_draft_picks(self, draft_id: str) -> List[Dict[str, Any]]:
        """
        Get all picks that have been made in a draft

        Args:
            draft_id: Sleeper draft ID

        Returns:
            List of picks (player_id, picked_by, roster_id, round, pick_no, metadata).
            For live drafts this updates in near-real-time as picks are made.
        """
        endpoint = f"draft/{draft_id}/picks"
        return await self._make_request(endpoint)

    async def get_draft_traded_picks(self, draft_id: str) -> List[Dict[str, Any]]:
        """
        Get traded picks within a specific draft

        Args:
            draft_id: Sleeper draft ID

        Returns:
            List of traded pick data
        """
        endpoint = f"draft/{draft_id}/traded_picks"
        return await self._make_request(endpoint)

    # ==================== PLAYER ENDPOINTS ====================

    async def get_all_players(self) -> Dict[str, Any]:
        """
        Get all NFL players

        Returns:
            Dictionary of all players keyed by player_id
            Warning: Large response (~10MB)
        """
        endpoint = f"players/{self.sport}"
        return await self._make_request(endpoint)

    async def get_trending_players(
        self,
        trend_type: str = "add",
        lookback_hours: int = 24,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Get trending players (most added/dropped)

        Args:
            trend_type: "add" or "drop"
            lookback_hours: Hours to look back (default 24)
            limit: Number of results (default 25)

        Returns:
            List of trending player data
        """
        endpoint = f"players/{self.sport}/trending/{trend_type}"
        params = f"?lookback_hours={lookback_hours}&limit={limit}"
        return await self._make_request(f"{endpoint}{params}")

    # ==================== STATS ENDPOINTS ====================

    async def get_player_stats(
        self,
        season: int,
        week: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get player stats for season or specific week

        Args:
            season: Year (e.g., 2024)
            week: Optional week number (None for full season)

        Returns:
            Dictionary of player stats keyed by player_id
        """
        if week:
            endpoint = f"stats/{self.sport}/regular/{season}/{week}"
        else:
            endpoint = f"stats/{self.sport}/regular/{season}"

        return await self._make_request(endpoint)

    async def get_player_projections(
        self,
        season: int,
        week: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get player projections for season or specific week

        Args:
            season: Year (e.g., 2024)
            week: Optional week number (None for full season)

        Returns:
            Dictionary of player projections keyed by player_id
        """
        if week:
            endpoint = f"projections/{self.sport}/regular/{season}/{week}"
        else:
            endpoint = f"projections/{self.sport}/regular/{season}"

        return await self._make_request(endpoint)

    # ==================== HELPER METHODS ====================

    async def get_team_roster(
        self,
        league_id: str,
        roster_id: int
    ) -> Dict[str, Any]:
        """
        Get a specific team's roster

        Args:
            league_id: Sleeper league ID
            roster_id: Roster ID (not user_id)

        Returns:
            Single roster data with players
        """
        rosters = await self.get_rosters(league_id)
        for roster in rosters:
            if roster.get("roster_id") == roster_id:
                return roster

        raise SleeperNotFoundError(f"Roster {roster_id} not found in league {league_id}")

    # ==================== AUTHENTICATED (GraphQL) ====================

    async def get_proposed_trades(
        self, league_id: str, token: str, limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Trade offers that have been made but not yet accepted.

        Sleeper's public v1 API only ever returns *completed* transactions, so
        an offer sitting in your inbox is invisible to it, which is why the
        app could not see a trade the website was showing. Pending offers live
        behind `sleeper.com/graphql`, which needs the user's own bearer token.

        Two details cost an afternoon each and are worth stating plainly:

        - The status is **"proposed"**, not "pending". Every sensible guess
          returns an empty list rather than an error.
        - `consenter_ids` holds the *roster ids* that have agreed so far. The
          proposing roster is always in it, so a roster missing from the list is
          the one still being asked, which is how incoming and outgoing offers
          are told apart.

        Returns [] rather than raising when the token is missing or rejected:
        a stale token should degrade the Offers tab, not break the page.
        """
        if not token:
            return []
        if settings.mock_mode:
            return mock_data.sleeper_proposed_trades()

        query = (
            "query {"
            f'  league_transactions_filtered(league_id: "{league_id}", '
            f'type_filters: ["trade"], limit: {int(limit)}) {{'
            "    transaction_id status type leg roster_ids adds drops"
            "    draft_picks creator created consenter_ids"
            "  }"
            "}"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://sleeper.com/graphql",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": token,
                        "User-Agent": "Mozilla/5.0 (compatible; FantasyFootballAssistant/1.0)",
                    },
                    json={"query": query},
                )
        except httpx.RequestError as e:
            logger.warning("Sleeper GraphQL unreachable", error=str(e))
            return []

        if response.status_code != 200:
            logger.warning(
                "Sleeper GraphQL rejected the request", status=response.status_code
            )
            return []

        payload = response.json()
        if payload.get("errors"):
            logger.warning(
                "Sleeper GraphQL returned errors",
                errors=str(payload["errors"])[:300],
            )
            return []

        rows = (payload.get("data") or {}).get("league_transactions_filtered") or []
        return [row for row in rows if row.get("status") == "proposed"]

    async def validate_league_access(self, league_id: str, user_id: str) -> bool:
        """
        Check if a user has access to a league

        Args:
            league_id: Sleeper league ID
            user_id: Sleeper user ID

        Returns:
            True if user is in league, False otherwise
        """
        try:
            users = await self.get_league_users(league_id)
            return any(user.get("user_id") == user_id for user in users)
        except SleeperError:
            return False

    def map_sleeper_to_standard_position(self, sleeper_position: str) -> str:
        """
        Map Sleeper position codes to standard position names

        Args:
            sleeper_position: Sleeper position code

        Returns:
            Standard position name
        """
        return self.position_map.get(sleeper_position, sleeper_position)


async def get_waiver_budgets(sleeper_league_id: str) -> List[Dict[str, Any]]:
    """FAAB budgets for every roster, in the same shape ESPN's returns.

    Sleeper splits this across three places: the league carries the budget
    (`settings.waiver_budget`), each roster carries what it has spent
    (`settings.waiver_budget_used`), and the bids themselves live in the
    transaction feed. Leagues that do not use FAAB have no budget at all —
    `waiver_type` 2 is FAAB, anything else is rolling or reverse-standings
    waivers — and those get an empty list rather than a fake 100.
    """
    # Imported lazily: draft_service imports SleeperService at module level.
    from app.services.draft_service import draft_service

    service = SleeperService()
    league = await service.get_league(sleeper_league_id)
    league_settings = league.get("settings") or {}

    total_budget = float(league_settings.get("waiver_budget") or 0)
    if not total_budget:
        logger.info("Sleeper league does not use FAAB", league_id=sleeper_league_id)
        return []

    rosters = await service.get_rosters(sleeper_league_id)
    players_map = await draft_service.get_players_cached()

    # Bids, newest first, bucketed by the roster that made them. Sleeper keys
    # transactions by week ("round"), so recent weeks are walked backwards.
    bids: Dict[int, List[Dict[str, Any]]] = {}
    current_week = int(league_settings.get("leg") or league.get("settings", {}).get("leg") or 0)
    weeks = [w for w in range(current_week, max(current_week - 4, 0), -1)] or [1]

    for week in weeks:
        try:
            transactions = await service.get_transactions(sleeper_league_id, week)
        except SleeperError as e:
            logger.warning("Sleeper transactions unavailable", week=week, error=str(e))
            continue

        for tx in transactions or []:
            if tx.get("type") != "waiver":
                continue
            bid = ((tx.get("settings") or {}).get("waiver_bid")) or 0
            for roster_id in tx.get("roster_ids") or []:
                player_id, player_name = _first_added_player(tx, players_map)
                bids.setdefault(roster_id, []).append({
                    "player_id": player_id,
                    "player_name": player_name,
                    "bid_amount": float(bid),
                    "status": "SUCCESSFUL" if tx.get("status") == "complete" else "FAILED",
                    "transaction_type": "ADD",
                    "week": week,
                })

    budgets = []
    for roster in rosters:
        roster_id = roster.get("roster_id")
        spent = float((roster.get("settings") or {}).get("waiver_budget_used") or 0)
        budgets.append({
            "team_id": roster_id,
            "team_name": "",  # resolved from the database by the caller
            "total_budget": total_budget,
            "spent_budget": spent,
            "current_budget": total_budget - spent,
            "recent_transactions": bids.get(roster_id, [])[:5],
        })
    return budgets


def _first_added_player(
    transaction: Dict[str, Any], players_map: Dict[str, Any]
) -> tuple[str, str]:
    """(id, name) for what a waiver claim was for. A bare id is useless in a UI."""
    for player_id in transaction.get("adds") or {}:
        meta = players_map.get(str(player_id)) or {}
        name = meta.get("full_name") or (
            f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip()
        )
        return str(player_id), (name or str(player_id))
    return "", "Waiver claim"


async def build_team_roster_entries(
    sleeper_league_id: str,
    sleeper_roster_id: int,
    week: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Build an ESPN-roster-shaped player list for one Sleeper roster.

    "ESPN-shaped" is a contract, not a vibe. Consumers — the roster page, the
    weekly primer, game day, the assistant's context, the cross-league view —
    all read `is_starter`, `on_injured_reserve`, `projected_points` and
    `applied_points`. An entry missing those does not fail loudly; it renders as
    a team with no starters and nought points, which is how Sleeper leagues came
    to look empty everywhere except the roster page.

    Points come from the week's matchup feed, which is where Sleeper puts them:
    `players_points` keyed by player id. Projections come from the season
    projection set, prorated across the regular season, because Sleeper does not
    publish a weekly projection.

    Raises SleeperNotFoundError if the roster is not in the league.
    """
    # Imported lazily: draft_service imports SleeperService at module level,
    # so a top-level import here would be circular.
    from app.services.draft_service import draft_service

    service = SleeperService()
    rosters = await service.get_rosters(sleeper_league_id)
    players_map = await draft_service.get_players_cached()
    roster_entry = next(
        (r for r in rosters if r.get("roster_id") == sleeper_roster_id), None
    )
    if roster_entry is None:
        raise SleeperNotFoundError(
            f"Roster {sleeper_roster_id} not found in league {sleeper_league_id}"
        )

    players_map = await draft_service.get_players_cached()
    starters = list(roster_entry.get("starters") or [])
    starter_set = set(starters)
    reserve = set(roster_entry.get("reserve") or [])

    # Sleeper's `starters` array is positional: entry i fills the i-th non-bench
    # slot of the league's `roster_positions`. Without that mapping a player in
    # the FLEX reads as whatever position he happens to play, which is wrong on
    # the one slot where knowing it matters.
    slot_by_player: Dict[str, str] = {}
    try:
        league_info = await service.get_league(sleeper_league_id)
        lineup_slots = [
            slot for slot in (league_info.get("roster_positions") or [])
            if slot not in ("BN", "IR", "TAXI")
        ]
        for index, pid in enumerate(starters):
            if index < len(lineup_slots):
                slot_by_player[pid] = lineup_slots[index]
    except SleeperError as e:
        logger.warning("Sleeper lineup slots unavailable", error=str(e))

    # Actual points for the week, if the matchup feed has them yet.
    week_points: Dict[str, float] = {}
    if week:
        try:
            for row in await service.get_matchups(sleeper_league_id, week) or []:
                if row.get("roster_id") == sleeper_roster_id:
                    week_points = row.get("players_points") or {}
                    break
        except SleeperError as e:
            logger.warning("Sleeper week points unavailable", error=str(e), week=week)

    # Sleeper publishes season projections, not weekly ones, so prorate.
    projections: Dict[str, Any] = {}
    try:
        projections = await draft_service._get_projections(settings.espn_season_year)
    except Exception as e:
        logger.warning("Sleeper projections unavailable", error=str(e))

    roster = []
    for pid in roster_entry.get("players") or []:
        meta = players_map.get(pid) or {}
        position = meta.get("position") or (meta.get("fantasy_positions") or ["UNKNOWN"])[0]
        full_name = meta.get("full_name") or (
            f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip() or str(pid)
        )
        is_starter = pid in starter_set
        on_ir = pid in reserve
        actual = round(float(week_points.get(pid) or 0), 2)

        season_proj = (projections.get(pid) or {}).get("pts_ppr")
        weekly_proj = round(float(season_proj) / REGULAR_SEASON_WEEKS, 2) if season_proj else actual

        roster.append({
            "player_id": pid,
            "full_name": full_name,
            "position_id": 0,
            "position_name": position,
            "lineup_slot_id": 21 if on_ir else (0 if is_starter else 20),
            "lineup_slot_name": (
                "IR" if on_ir
                else (slot_by_player.get(pid) or position) if is_starter
                else "BENCH"
            ),
            # The contract the rest of the app reads. Derived here so no caller
            # has to re-derive a starter from a slot name.
            "is_starter": is_starter and not on_ir,
            "on_injured_reserve": on_ir,
            "pro_team_id": 0,
            "pro_team_abbr": meta.get("team"),
            "eligible_slots": [],
            "projected_points": weekly_proj,
            "applied_points": actual,
            "season_points": actual,
            "stats": {"actual": {}, "projected": {}},
            "injury_status": meta.get("injury_status"),
        })
    # Starters first, in lineup order; bench after.
    order = {pid: i for i, pid in enumerate(starters)}
    roster.sort(key=lambda p: order.get(p["player_id"], len(order) + 1))
    return roster


FANTASY_POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")


async def get_free_agents(
    sleeper_league_id: str,
    position: Optional[str] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Players in the pool that nobody in this league rosters.

    Sleeper publishes no free-agent endpoint: the pool is everyone in the
    player dictionary minus everyone on a roster, so it has to be derived. The
    dictionary is ~10MB, which is why this goes through the shared cache rather
    than fetching its own copy.

    Ranked by prorated season projection, the same number the roster entries
    carry, so a free agent and a bench player can be compared directly.
    """
    from app.services.draft_service import draft_service

    service = SleeperService()
    rosters = await service.get_rosters(sleeper_league_id)
    players_map = await draft_service.get_players_cached()
    projections = await draft_service._get_projections(settings.espn_season_year)

    rostered: set = set()
    for roster in rosters or []:
        for pid in (roster.get("players") or []):
            rostered.add(str(pid))

    wanted = position.upper() if position else None
    if wanted == "D/ST":
        wanted = "DEF"

    out: List[Dict[str, Any]] = []
    for pid, meta in (players_map or {}).items():
        if str(pid) in rostered:
            continue
        if not isinstance(meta, dict):
            continue

        pos = meta.get("position")
        if pos not in FANTASY_POSITIONS:
            continue
        if wanted and pos != wanted:
            continue
        # Someone who is not on an NFL roster cannot help this week.
        if pos != "DEF" and not meta.get("team"):
            continue

        season_proj = (projections.get(str(pid)) or {}).get("pts_ppr")
        if not season_proj:
            continue

        out.append({
            "player_id": str(pid),
            "full_name": meta.get("full_name")
            or f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip()
            or str(pid),
            "position_name": "D/ST" if pos == "DEF" else pos,
            "pro_team_abbr": meta.get("team"),
            "projected_points": round(float(season_proj) / REGULAR_SEASON_WEEKS, 2),
            "injury_status": meta.get("injury_status"),
        })

    out.sort(key=lambda p: p["projected_points"], reverse=True)
    return out[:limit]
