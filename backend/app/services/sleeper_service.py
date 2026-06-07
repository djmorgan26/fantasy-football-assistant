"""
Sleeper Fantasy Football API Service
Provides async interface to Sleeper API endpoints
API Documentation: https://docs.sleeper.app/
"""
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

from app.core.config import settings
from app.services import mock_data

logger = structlog.get_logger()


class SleeperError(Exception):
    """Base exception for Sleeper API errors"""
    pass


class SleeperConnectionError(SleeperError):
    """Exception for connection errors"""
    pass


class SleeperNotFoundError(SleeperError):
    """Exception for 404 errors"""
    pass


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

    async def _make_request(
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
            if tail in ("transactions", "traded_picks", "winners_bracket", "losers_bracket"):
                return []
            return mock_data.sleeper_league()

        logger.warning("Unmapped mock Sleeper endpoint", endpoint=endpoint)
        return {}

    # ==================== USER ENDPOINTS ====================

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


async def build_team_roster_entries(
    sleeper_league_id: str, sleeper_roster_id: int
) -> List[Dict[str, Any]]:
    """Build an ESPN-roster-shaped player list for one Sleeper roster.

    Shared by the teams and suggestions APIs so Sleeper leagues get the same
    response shape the frontend renders for ESPN rosters. Returns None-safe
    data even when player metadata is missing. Raises SleeperNotFoundError if
    the roster is not in the league.
    """
    # Imported lazily: draft_service imports SleeperService at module level,
    # so a top-level import here would be circular.
    from app.services.draft_service import draft_service

    service = SleeperService()
    rosters = await service.get_rosters(sleeper_league_id)
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

    roster = []
    for pid in roster_entry.get("players") or []:
        meta = players_map.get(pid) or {}
        position = meta.get("position") or (meta.get("fantasy_positions") or ["UNKNOWN"])[0]
        full_name = meta.get("full_name") or (
            f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip() or str(pid)
        )
        is_starter = pid in starter_set
        roster.append({
            "player_id": pid,
            "full_name": full_name,
            "position_id": 0,
            "position_name": position,
            "lineup_slot_id": 0 if is_starter else 20,
            "lineup_slot_name": position if is_starter else "BENCH",
            "pro_team_id": 0,
            "pro_team_abbr": meta.get("team"),
            "eligible_slots": [],
            "stats": {"actual": {}, "projected": {}},
            "injury_status": meta.get("injury_status"),
        })
    # Starters first, in lineup order; bench after.
    order = {pid: i for i, pid in enumerate(starters)}
    roster.sort(key=lambda p: order.get(p["player_id"], len(order) + 1))
    return roster
