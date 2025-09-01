from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MatchupBase(BaseModel):
    matchup_id: int
    league_id: int
    week: int
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    home_score: float = 0.0
    away_score: float = 0.0
    is_playoff: bool = False
    winner: str = "UNDECIDED"


class MatchupCreate(MatchupBase):
    pass


class MatchupUpdate(BaseModel):
    home_score: Optional[float] = None
    away_score: Optional[float] = None
    winner: Optional[str] = None


class MatchupResponse(MatchupBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MatchupWithTeams(MatchupResponse):
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    home_team_location: Optional[str] = None
    away_team_location: Optional[str] = None
    home_team_nickname: Optional[str] = None
    away_team_nickname: Optional[str] = None