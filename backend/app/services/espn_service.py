import asyncio
import json
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class ESPNCookies:
    def __init__(self, espn_s2: str = None, swid: str = None):
        self.espn_s2 = espn_s2
        self.swid = swid
    
    def to_dict(self) -> Dict[str, str]:
        cookies = {}
        if self.espn_s2:
            cookies["espn_s2"] = self.espn_s2
        if self.swid:
            cookies["SWID"] = self.swid
        return cookies


class ESPNService:
    def __init__(self):
        self.base_url = settings.espn_api_base_url
        self.season_year = settings.espn_season_year
        self.timeout = httpx.Timeout(30.0)
        self.rate_limit_requests = settings.espn_rate_limit_requests
        self.rate_limit_window = settings.espn_rate_limit_window
        
        # Position mappings
        self.position_map = {
            0: "QB", 1: "TQB", 2: "RB", 3: "RB/WR", 4: "WR",
            5: "WR/TE", 6: "TE", 16: "D/ST", 17: "K", 20: "BENCH",
            21: "IR", 23: "FLEX"
        }
        
        # Lineup slot mappings
        self.lineup_slots = {
            0: "QB", 2: "RB", 4: "WR", 6: "TE", 16: "D/ST",
            17: "K", 20: "BENCH", 21: "IR", 23: "FLEX"
        }

    async def _make_request(
        self,
        endpoint: str,
        cookies: Optional[ESPNCookies] = None,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/seasons/{self.season_year}/segments/0/leagues/{endpoint}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; FantasyFootballAssistant/1.0)",
            "Accept": "application/json"
        }
        
        cookie_dict = cookies.to_dict() if cookies else {}
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        url, 
                        headers=headers, 
                        cookies=cookie_dict,
                        params=params or {}
                    )
                    
                    if response.status_code == 200:
                        logger.info("ESPN API request successful", url=url, content_length=len(response.text))
                        
                        # Ensure we have content
                        if not response.text:
                            logger.error("ESPN API returned empty response")
                            raise ESPNConnectionError("Empty response from ESPN API")
                        
                        # Parse JSON response
                        try:
                            json_data = response.json()
                            logger.info("Successfully parsed JSON response", 
                                      response_type=type(json_data).__name__, 
                                      keys=list(json_data.keys())[:10] if isinstance(json_data, dict) else "Not a dict")
                            
                            # ESPN API should always return a dict
                            if not isinstance(json_data, dict):
                                logger.error("ESPN API returned unexpected data type", 
                                           expected="dict", 
                                           actual=type(json_data).__name__, 
                                           content=str(json_data)[:500])
                                raise ESPNConnectionError(f"ESPN API returned {type(json_data).__name__}, expected dict")
                            
                            return json_data
                            
                        except json.JSONDecodeError as e:
                            logger.error("Failed to parse ESPN API response as JSON", 
                                       error=str(e),
                                       content_preview=response.text[:500])
                            raise ESPNConnectionError(f"Invalid JSON from ESPN API: {e}")
                        except Exception as e:
                            logger.error("Unexpected error parsing ESPN API response", 
                                       error=str(e),
                                       error_type=type(e).__name__)
                            raise ESPNConnectionError(f"Failed to process ESPN API response: {e}")
                    elif response.status_code == 401:
                        logger.warning("ESPN API authentication failed", url=url)
                        raise ESPNAuthenticationError("Invalid ESPN credentials")
                    elif response.status_code == 429:
                        wait_time = 2 ** attempt
                        logger.warning("ESPN API rate limited, retrying", wait_time=wait_time)
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error("ESPN API request failed", 
                                   status_code=response.status_code, url=url)
                        response.raise_for_status()
                        
            except httpx.RequestError as e:
                logger.error("ESPN API request error", error=str(e), attempt=attempt)
                if attempt == max_retries - 1:
                    raise ESPNConnectionError(f"Failed to connect to ESPN API: {e}")
                await asyncio.sleep(1)
        
        raise ESPNConnectionError("Max retries exceeded")

    async def get_league_info(
        self, 
        league_id: str, 
        cookies: Optional[ESPNCookies] = None
    ) -> Dict[str, Any]:
        try:
            data = await self._make_request(f"{league_id}", cookies)
            return {
                "id": data.get("id"),
                "name": data.get("settings", {}).get("name", "Unknown League"),
                "size": len(data.get("teams", [])),
                "current_week": data.get("scoringPeriodId", 1),
                "current_matchup_period": data.get("status", {}).get("currentMatchupPeriod", 1),
                "is_active": data.get("status", {}).get("isActive", False),
                "scoring_type": self._determine_scoring_type(data),
                "roster_settings": self._extract_roster_settings(data),
                "scoring_settings": self._extract_scoring_settings(data)
            }
        except Exception as e:
            logger.error("Failed to get league info", league_id=league_id, error=str(e))
            raise

    async def get_teams(
        self, 
        league_id: str, 
        cookies: Optional[ESPNCookies] = None
    ) -> List[Dict[str, Any]]:
        try:
            data = await self._make_request(f"{league_id}", cookies, {"view": "mTeam"})
            logger.info("ESPN API response type", data_type=type(data).__name__)
            
            # Ensure data is a dictionary
            if not isinstance(data, dict):
                logger.error("ESPN API returned non-dict data for teams", 
                           league_id=league_id, 
                           data_type=type(data), 
                           data_preview=str(data)[:500])
                raise ESPNConnectionError(f"Invalid response format from ESPN API: expected dict, got {type(data)}")
            
            logger.info("Data has keys", keys=list(data.keys()) if data else [])
            logger.info("Teams data type and preview", 
                       teams_type=type(data.get("teams", [])).__name__,
                       teams_preview=str(data.get("teams", []))[:200])
            teams = []
            
            for team_data in data.get("teams", []):
                logger.info("Processing team data", 
                           team_data_type=type(team_data).__name__,
                           team_preview=str(team_data)[:200] if isinstance(team_data, dict) else str(team_data))
                
                # Skip if team_data is not a dict (should not happen with proper ESPN API)
                if not isinstance(team_data, dict):
                    logger.warning("Skipping non-dict team data", data=str(team_data))
                    continue
                    
                # Create a friendly team name
                # Try to get the custom team name first (this is what users set in ESPN)
                team_name = team_data.get("name", "").strip()
                location = team_data.get("location", "").strip()
                nickname = team_data.get("nickname", "").strip()
                abbrev = team_data.get("abbrev", "").strip()
                
                # Log the raw ESPN data for debugging
                logger.info("ESPN team data fields", 
                           team_id=team_data.get("id"),
                           name=team_name,
                           location=location, 
                           nickname=nickname,
                           abbrev=abbrev)
                
                # Priority order: custom name > location + nickname > location > nickname > abbrev
                if team_name:
                    display_name = team_name
                elif location and nickname:
                    display_name = f"{location} {nickname}"
                elif location:
                    display_name = location
                elif nickname:
                    display_name = nickname
                elif abbrev:
                    display_name = f"Team {abbrev}"
                else:
                    display_name = f"Team {team_data.get('id', 'Unknown')}"
                
                teams.append({
                    "id": team_data.get("id"),
                    "name": display_name,
                    "location": location,
                    "nickname": nickname,
                    "abbreviation": abbrev,
                    "logo_url": team_data.get("logo", ""),
                    "wins": team_data.get("record", {}).get("overall", {}).get("wins", 0),
                    "losses": team_data.get("record", {}).get("overall", {}).get("losses", 0),
                    "ties": team_data.get("record", {}).get("overall", {}).get("ties", 0),
                    "points_for": team_data.get("record", {}).get("overall", {}).get("pointsFor", 0.0),
                    "points_against": team_data.get("record", {}).get("overall", {}).get("pointsAgainst", 0.0),
                    "owners": [owner.get("id") if isinstance(owner, dict) else owner for owner in team_data.get("owners", [])]
                })
            
            return teams
        except Exception as e:
            logger.error("Failed to get teams", league_id=league_id, error=str(e), 
                        error_type=type(e).__name__, traceback=str(e))
            raise

    async def get_team_roster(
        self, 
        league_id: str, 
        team_id: int,
        week: Optional[int] = None,
        cookies: Optional[ESPNCookies] = None
    ) -> Dict[str, Any]:
        try:
            params = {"view": "mRoster"}
            if week:
                params["scoringPeriodId"] = week
                
            data = await self._make_request(f"{league_id}", cookies, params)
            
            # Find the specific team
            team_data = None
            for team in data.get("teams", []):
                if team.get("id") == team_id:
                    team_data = team
                    break
            
            if not team_data:
                raise ESPNDataError(f"Team {team_id} not found in league {league_id}")
            
            roster = []
            roster_entries = team_data.get("roster", {}).get("entries", [])
            
            for entry in roster_entries:
                player = entry.get("playerPoolEntry", {}).get("player", {})
                roster.append({
                    "player_id": player.get("id"),
                    "full_name": player.get("fullName", ""),
                    "position_id": player.get("defaultPositionId"),
                    "position_name": self.position_map.get(player.get("defaultPositionId"), "UNKNOWN"),
                    "lineup_slot_id": entry.get("lineupSlotId"),
                    "lineup_slot_name": self.lineup_slots.get(entry.get("lineupSlotId"), "UNKNOWN"),
                    "pro_team_id": player.get("proTeamId"),
                    "eligible_slots": player.get("eligibleSlots", []),
                    "stats": self._extract_player_stats(player, week)
                })
            
            return {
                "team_id": team_id,
                "roster": roster,
                "week": week or data.get("scoringPeriodId", 1)
            }
        except Exception as e:
            logger.error("Failed to get team roster", 
                        league_id=league_id, team_id=team_id, error=str(e))
            raise

    async def get_available_players(
        self, 
        league_id: str,
        week: Optional[int] = None,
        position: Optional[str] = None,
        cookies: Optional[ESPNCookies] = None
    ) -> List[Dict[str, Any]]:
        try:
            # Use players_wl view to get available players (kona_player_info changes data structure)
            params = {
                "view": "players_wl",
                "scoringPeriodId": week or 1
            }
                
            data = await self._make_request(f"{league_id}", cookies, params)
            
            players = []
            for player_data in data.get("players", []):
                player = player_data.get("player", {})
                
                # Filter by position if specified
                if position and self.position_map.get(player.get("defaultPositionId")) != position:
                    continue
                
                # Check if player is available (not on any roster)
                if player_data.get("onTeamId") is not None:
                    continue
                
                # Get season and last week points for better data
                season_points = 0.0
                last_week_points = 0.0
                avg_points = 0.0
                
                player_stats = self._extract_player_stats(player, week)
                projected_points = self._get_projected_points(player, week)
                
                # Try to get season totals
                for stat_entry in player.get("stats", []):
                    if stat_entry.get("statSourceId") == 0:  # Actual stats
                        season_points += stat_entry.get("appliedTotal", 0.0)
                        
                if season_points > 0:
                    # Estimate average (assuming we're in week 17 or so)
                    avg_points = season_points / 17.0

                players.append({
                    "id": player.get("id"),
                    "espn_player_id": player.get("id"),
                    "full_name": player.get("fullName", ""),
                    "first_name": player.get("firstName", ""),
                    "last_name": player.get("lastName", ""),
                    "position_id": player.get("defaultPositionId"),
                    "position_name": self.position_map.get(player.get("defaultPositionId"), "UNKNOWN"),
                    "pro_team_id": player.get("proTeamId"),
                    "pro_team_abbr": self._get_pro_team_abbr(player.get("proTeamId")),
                    "eligible_slots": player.get("eligibleSlots", []),
                    "is_active": player.get("injuryStatus", "ACTIVE") == "ACTIVE",
                    "injury_status": player.get("injuryStatus", "ACTIVE"),
                    "stats": player_stats,
                    "season_points": season_points,
                    "last_week_points": last_week_points,
                    "average_points": avg_points,
                    "projected_points": projected_points,
                    "ownership_percentage": player_data.get("ratings", {}).get("0", {}).get("positionalRanking", 0.0),
                    "latest_news": player.get("news", {}).get("headline", ""),
                    "news_updated": player.get("news", {}).get("timeStamp")
                })
            
            # Sort by projected points descending
            players.sort(key=lambda p: p.get("projected_points", 0), reverse=True)
            
            return players
        except Exception as e:
            logger.error("Failed to get available players", 
                        league_id=league_id, error=str(e))
            raise

    async def get_matchups(
        self, 
        league_id: str,
        week: Optional[int] = None,
        cookies: Optional[ESPNCookies] = None
    ) -> List[Dict[str, Any]]:
        try:
            # Use multiple views for complete matchup data including live scoring
            params = {"view": ["mMatchup", "mScoreboard", "mLiveScoring"]}
            if week:
                params["scoringPeriodId"] = week
                
            data = await self._make_request(f"{league_id}", cookies, params)
            
            matchups = []
            for matchup_data in data.get("schedule", []):
                if week and matchup_data.get("matchupPeriodId") != week:
                    continue
                
                # Calculate projected scores from roster data if available
                home_projected = await self._calculate_team_projected_score(
                    matchup_data.get("home", {}), league_id, week or 1, cookies
                )
                away_projected = await self._calculate_team_projected_score(
                    matchup_data.get("away", {}), league_id, week or 1, cookies
                )
                
                # Try to get scoring data from multiple sources
                home_data = matchup_data.get("home", {})
                away_data = matchup_data.get("away", {})
                
                # Get the current week for score lookup
                current_week = matchup_data.get("matchupPeriodId", week or 1)
                
                # Get live scoring data with proper fallback logic
                def get_team_score(team_data, week):
                    # Priority 1: totalPointsLive (real-time scoring during games)
                    if "totalPointsLive" in team_data:
                        return team_data["totalPointsLive"]
                    # Priority 2: pointsByScoringPeriod for the current week  
                    elif "pointsByScoringPeriod" in team_data:
                        week_scores = team_data["pointsByScoringPeriod"]
                        if str(week) in week_scores:
                            return week_scores[str(week)]
                    # Priority 3: totalPoints (final scores)
                    return team_data.get("totalPoints", 0)
                
                home_score = get_team_score(home_data, current_week)
                away_score = get_team_score(away_data, current_week)
                
                matchups.append({
                    "matchup_id": matchup_data.get("id"),
                    "week": matchup_data.get("matchupPeriodId"),
                    "home_team_id": home_data.get("teamId"),
                    "away_team_id": away_data.get("teamId"),
                    "home_score": home_score,
                    "away_score": away_score,
                    "home_projected_score": home_projected,
                    "away_projected_score": away_projected,
                    "is_playoff": matchup_data.get("playoffTierType") not in [None, "NONE"],
                    "winner": matchup_data.get("winner", "UNDECIDED")
                })
            
            return matchups
        except Exception as e:
            logger.error("Failed to get matchups", 
                        league_id=league_id, week=week, error=str(e))
            raise

    async def _calculate_team_projected_score(
        self,
        team_data: Dict[str, Any],
        league_id: str,
        week: int,
        cookies: Optional[ESPNCookies] = None
    ) -> Optional[float]:
        """Calculate projected score for a team based on their starting lineup"""
        try:
            team_id = team_data.get("teamId")
            if not team_id:
                return None
            
            # Get raw roster data directly from ESPN API to access the original player stats
            params = {"view": "mRoster", "scoringPeriodId": week}
            data = await self._make_request(f"{league_id}", cookies, params)
            
            # Find the specific team
            team_data_raw = None
            for team in data.get("teams", []):
                if team.get("id") == team_id:
                    team_data_raw = team
                    break
            
            if not team_data_raw:
                return None
            
            projected_total = 0.0
            roster_entries = team_data_raw.get("roster", {}).get("entries", [])
            
            for entry in roster_entries:
                lineup_slot = entry.get("lineupSlotId", 0)
                # Only count starting lineup players (exclude bench=20, IR=21)  
                if lineup_slot != 20 and lineup_slot != 21:  # Not bench or IR
                    player = entry.get("playerPoolEntry", {}).get("player", {})
                    # Use the existing _get_projected_points method with raw player data
                    projected_points = self._get_projected_points(player, week)
                    projected_total += projected_points
                    
            return projected_total if projected_total > 0 else None
            
        except Exception as e:
            logger.warning(f"Failed to calculate projected score for team {team_data.get('teamId', 'unknown')}: {e}")
            return None

    def _get_projected_points_for_roster_player(self, player_data: Dict[str, Any]) -> float:
        """Extract projected points from roster player data"""
        try:
            stats = player_data.get("stats", {})
            projected = stats.get("projected", {})
            
            # Try different potential keys for total projected points
            # Based on debug output, '0' seems to be the main key for totals
            if "0" in projected:
                return float(projected["0"])
            
            # If that doesn't work, try other common keys from debug output
            for key in ["213", "210"]:  # These appeared in debug output
                if key in projected:
                    return float(projected[key])
            
            # If we still can't find it, let's look for the highest value
            # which is likely the total projected points
            if projected:
                max_value = max(float(v) for v in projected.values() if isinstance(v, (int, float)))
                return max_value
            
            return 0.0
            
        except (ValueError, TypeError, KeyError, AttributeError):
            return 0.0

    async def get_waiver_budgets(
        self, 
        league_id: str,
        cookies: Optional[ESPNCookies] = None
    ) -> List[Dict[str, Any]]:
        try:
            data = await self._make_request(f"{league_id}", cookies, {"view": "mTeam"})
            
            budgets = []
            for team_data in data.get("teams", []):
                # ESPN stores acquisition budget info in team settings
                acquisitions = team_data.get("transactionCounter", {})
                budget_used = acquisitions.get("acquisitionBudgetSpent", 0)
                
                # Default budget is usually 100, but check league settings
                league_settings = data.get("settings", {})
                total_budget = league_settings.get("acquisitionSettings", {}).get("budget", 100)
                
                budgets.append({
                    "team_id": team_data.get("id"),
                    "team_name": team_data.get("name", ""),
                    "total_budget": float(total_budget),
                    "spent_budget": float(budget_used),
                    "current_budget": float(total_budget - budget_used)
                })
            
            return budgets
        except Exception as e:
            logger.error("Failed to get waiver budgets", 
                        league_id=league_id, error=str(e))
            raise

    async def validate_trade(
        self, 
        league_id: str,
        proposing_team_id: int,
        receiving_team_id: int,
        give_players: List[int],
        receive_players: List[int],
        cookies: Optional[ESPNCookies] = None
    ) -> Dict[str, Any]:
        try:
            # Get current rosters for both teams
            proposing_roster = await self.get_team_roster(league_id, proposing_team_id, cookies=cookies)
            receiving_roster = await self.get_team_roster(league_id, receiving_team_id, cookies=cookies)
            
            # Validate players exist on respective rosters
            proposing_player_ids = [p["player_id"] for p in proposing_roster["roster"]]
            receiving_player_ids = [p["player_id"] for p in receiving_roster["roster"]]
            
            for player_id in give_players:
                if player_id not in proposing_player_ids:
                    raise ESPNValidationError(f"Player {player_id} not on proposing team roster")
            
            for player_id in receive_players:
                if player_id not in receiving_player_ids:
                    raise ESPNValidationError(f"Player {player_id} not on receiving team roster")
            
            # Calculate roster implications
            # This is a simplified validation - ESPN has complex roster rules
            return {
                "is_valid": True,
                "proposing_team_id": proposing_team_id,
                "receiving_team_id": receiving_team_id,
                "give_players": give_players,
                "receive_players": receive_players,
                "validation_message": "Trade appears valid based on current rosters"
            }
            
        except Exception as e:
            logger.error("Failed to validate trade", 
                        league_id=league_id, error=str(e))
            return {
                "is_valid": False,
                "error": str(e)
            }

    def _determine_scoring_type(self, league_data: Dict[str, Any]) -> str:
        scoring_items = league_data.get("settings", {}).get("scoringSettings", {}).get("scoringItems", [])
        
        # Look for PPR scoring
        for item in scoring_items:
            if item.get("statId") == 53:  # Receptions
                points = item.get("points", 0)
                if points == 1.0:
                    return "ppr"
                elif points == 0.5:
                    return "half_ppr"
        
        return "standard"

    def _extract_roster_settings(self, league_data: Dict[str, Any]) -> Dict[str, Any]:
        roster_settings = league_data.get("settings", {}).get("rosterSettings", {})
        return {
            "roster_size": roster_settings.get("rosterSize", 16),
            "position_limits": roster_settings.get("positionLimits", {}),
            "lineup_slots": roster_settings.get("lineupSlotCounts", {})
        }

    def _extract_scoring_settings(self, league_data: Dict[str, Any]) -> Dict[str, Any]:
        scoring_settings = league_data.get("settings", {}).get("scoringSettings", {})
        return {
            "scoring_items": scoring_settings.get("scoringItems", []),
            "player_rank_type": scoring_settings.get("playerRankType", "STANDARD"),
            "scoring_type": scoring_settings.get("scoringType", "H2H_POINTS")
        }

    def _extract_player_stats(self, player_data: Dict[str, Any], week: Optional[int] = None) -> Dict[str, Any]:
        stats = {}
        
        for stat_entry in player_data.get("stats", []):
            if week and stat_entry.get("scoringPeriodId") != week:
                continue
                
            stat_source = stat_entry.get("statSourceId", 0)
            if stat_source == 0:  # Actual stats
                stats["actual"] = stat_entry.get("stats", {})
            elif stat_source == 1:  # Projected stats
                stats["projected"] = stat_entry.get("stats", {})
        
        return stats

    def _get_projected_points(self, player_data: Dict[str, Any], week: Optional[int] = None) -> float:
        for stat_entry in player_data.get("stats", []):
            if week and stat_entry.get("scoringPeriodId") != week:
                continue
                
            if stat_entry.get("statSourceId") == 1:  # Projected stats
                return stat_entry.get("appliedTotal", 0.0)
        
        return 0.0
    
    def _get_pro_team_abbr(self, pro_team_id: Optional[int]) -> str:
        """Get NFL team abbreviation from pro team ID"""
        # ESPN pro team ID mappings (partial list)
        team_map = {
            1: "ATL", 2: "BUF", 3: "CHI", 4: "CIN", 5: "CLE", 6: "DAL", 7: "DEN",
            8: "DET", 9: "GB", 10: "TEN", 11: "IND", 12: "KC", 13: "LV", 14: "LAR",
            15: "MIA", 16: "MIN", 17: "NE", 18: "NO", 19: "NYG", 20: "NYJ",
            21: "PHI", 22: "ARI", 23: "PIT", 24: "LAC", 25: "SF", 26: "SEA",
            27: "TB", 28: "WAS", 29: "CAR", 30: "JAX", 33: "BAL", 34: "HOU"
        }
        return team_map.get(pro_team_id, "FA")


class ESPNError(Exception):
    pass


class ESPNAuthenticationError(ESPNError):
    pass


class ESPNConnectionError(ESPNError):
    pass


class ESPNDataError(ESPNError):
    pass


class ESPNValidationError(ESPNError):
    pass