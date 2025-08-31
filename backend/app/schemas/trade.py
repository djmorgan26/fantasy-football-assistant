from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TradeStatusEnum(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TradeCreate(BaseModel):
    league_id: int
    proposing_team_id: int
    receiving_team_id: int
    give_players: List[int] = Field(description="Player IDs being given away")
    receive_players: List[int] = Field(description="Player IDs being received")


class TradeAnalysisRequest(BaseModel):
    league_id: int
    proposing_team_id: int
    receiving_team_id: int
    give_players: List[int]
    receive_players: List[int]


class TradeResponse(BaseModel):
    id: int
    league_id: int
    proposing_team_id: int
    receiving_team_id: int
    proposed_players: Dict[str, List[int]]
    status: TradeStatusEnum
    fairness_score: Optional[float] = None
    value_difference: Optional[float] = None
    analysis_summary: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TradeAnalysisResponse(BaseModel):
    is_valid: bool
    fairness_score: Optional[float] = None
    value_difference: Optional[float] = None
    analysis_summary: str
    recommendations: List[str] = []
    player_details: Dict[str, Any] = {}