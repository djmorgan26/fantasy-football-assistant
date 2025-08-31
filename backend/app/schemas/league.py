from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class LeagueBase(BaseModel):
    espn_league_id: int
    name: str
    season_year: int = Field(default=2024)


class LeagueCreate(LeagueBase):
    espn_s2: Optional[str] = Field(None, description="ESPN S2 cookie for private leagues")
    espn_swid: Optional[str] = Field(None, description="ESPN SWID cookie for private leagues")


class LeagueUpdate(BaseModel):
    name: Optional[str] = None
    espn_s2: Optional[str] = None
    espn_swid: Optional[str] = None


class LeagueResponse(LeagueBase):
    id: int
    size: int
    scoring_type: str
    current_week: int
    is_public: bool
    is_active: bool
    roster_settings: Optional[Dict[str, Any]] = None
    scoring_settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    last_synced: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LeagueConnectionRequest(BaseModel):
    league_id: int = Field(description="ESPN League ID")
    espn_s2: Optional[str] = Field(None, description="ESPN S2 cookie for private leagues")
    espn_swid: Optional[str] = Field(None, description="ESPN SWID cookie for private leagues")


class LeagueConnectionResponse(BaseModel):
    success: bool
    message: str
    league: Optional[LeagueResponse] = None
    teams: Optional[List[Dict[str, Any]]] = None