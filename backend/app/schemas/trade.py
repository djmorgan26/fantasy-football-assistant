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
    league_id: int = Field(gt=0, description="League ID must be positive")
    proposing_team_id: int = Field(gt=0, description="Proposing team ID must be positive")
    receiving_team_id: int = Field(gt=0, description="Receiving team ID must be positive")
    give_players: List[int] = Field(min_length=1, max_length=10, description="Player IDs being given away (1-10 players)")
    receive_players: List[int] = Field(min_length=1, max_length=10, description="Player IDs being received (1-10 players)")

    @staticmethod
    def validate_different_teams(proposing_team_id: int, receiving_team_id: int) -> None:
        if proposing_team_id == receiving_team_id:
            raise ValueError("Cannot trade with yourself")

    def model_post_init(self, __context):
        self.validate_different_teams(self.proposing_team_id, self.receiving_team_id)


class TradeAnalysisRequest(BaseModel):
    league_id: int = Field(gt=0, description="League ID must be positive")
    proposing_team_id: int = Field(gt=0, description="Proposing team ID must be positive")
    receiving_team_id: int = Field(gt=0, description="Receiving team ID must be positive")
    give_players: List[int] = Field(min_length=1, max_length=10, description="1-10 players to give")
    receive_players: List[int] = Field(min_length=1, max_length=10, description="1-10 players to receive")

    @staticmethod
    def validate_different_teams(proposing_team_id: int, receiving_team_id: int) -> None:
        if proposing_team_id == receiving_team_id:
            raise ValueError("Cannot analyze trade with same team")

    def model_post_init(self, __context):
        self.validate_different_teams(self.proposing_team_id, self.receiving_team_id)


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