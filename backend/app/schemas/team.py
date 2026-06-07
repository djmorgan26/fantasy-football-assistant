from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class TeamResponse(BaseModel):
    id: int
    # Platform-specific identifiers: ESPN teams have espn_team_id, Sleeper
    # teams have sleeper_roster_id. Each is None on the other platform.
    espn_team_id: Optional[int] = None
    sleeper_roster_id: Optional[int] = None
    name: str
    location: Optional[str] = None
    nickname: Optional[str] = None
    abbreviation: Optional[str] = None
    logo_url: Optional[str] = None
    wins: int
    losses: int
    ties: int
    points_for: float
    points_against: float
    current_roster: Optional[List[Dict[str, Any]]] = None
    owner_user_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class RosterResponse(BaseModel):
    team_id: int
    week: int
    roster: List[Dict[str, Any]]