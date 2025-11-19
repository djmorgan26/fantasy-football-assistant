"""
Pydantic schemas for Sleeper API requests and responses
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class SleeperLeagueConnectionRequest(BaseModel):
    """Request to connect a Sleeper league"""
    league_id: str = Field(description="Sleeper league ID")
    sleeper_user_id: str = Field(description="Sleeper user ID or username")


class SleeperLeagueConnectionResponse(BaseModel):
    """Response after connecting a Sleeper league"""
    success: bool
    message: str
    league_id: int
    sleeper_league_id: str
    league_name: str
    teams_synced: int


class SleeperUserLeaguesResponse(BaseModel):
    """Response containing user's Sleeper leagues"""
    user_id: str
    username: str
    season: int
    leagues: List[Dict[str, Any]]


class MatchupResponse(BaseModel):
    """Sleeper matchup response"""
    roster_id: int
    matchup_id: Optional[int]
    points: float
    starters: List[str]
    players: List[str]
