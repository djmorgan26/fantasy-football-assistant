from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class PlayerResponse(BaseModel):
    id: int
    espn_player_id: int
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position_id: int
    position_name: Optional[str] = None
    pro_team_id: Optional[int] = None
    pro_team_abbr: Optional[str] = None
    eligible_slots: Optional[List[int]] = None
    is_active: bool
    injury_status: Optional[str] = None
    season_stats: Optional[Dict[str, Any]] = None
    last_week_points: float
    season_points: float
    average_points: float
    latest_news: Optional[str] = None
    news_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PlayerSearchRequest(BaseModel):
    league_id: int
    week: Optional[int] = None
    position: Optional[str] = None
    search_term: Optional[str] = None
    available_only: bool = True


class PlayerSearchResponse(BaseModel):
    players: List[Dict[str, Any]]
    total_count: int