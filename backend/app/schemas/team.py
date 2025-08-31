from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class TeamResponse(BaseModel):
    id: int
    espn_team_id: int
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
    
    class Config:
        from_attributes = True


class RosterResponse(BaseModel):
    team_id: int
    week: int
    roster: List[Dict[str, Any]]