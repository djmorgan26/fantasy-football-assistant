"""
Pydantic schemas for draft preparation and the live draft assistant.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ValueBoardPlayer(BaseModel):
    """A single player on the league-scoring-adjusted value board."""
    player_id: str
    name: str
    position: str
    team: Optional[str] = None
    projected_points: float
    vbd: float = Field(description="Value over replacement-level starter")
    overall_rank: Optional[int] = None
    position_rank: Optional[int] = None
    tier: Optional[int] = None
    adp: Optional[float] = Field(default=None, description="Approx average draft position")
    bye_week: Optional[int] = None
    age: Optional[int] = None
    injury_status: Optional[str] = None

    class Config:
        from_attributes = True


class ValueBoardResponse(BaseModel):
    """Full draft value board response."""
    season: int
    scoring: str
    team_count: int
    player_count: int
    replacement_ranks: Dict[str, int]
    players: List[ValueBoardPlayer]


class DraftPickRecommendation(ValueBoardPlayer):
    """A value-board player annotated with live-draft pick scoring."""
    need_bonus: Optional[float] = None
    pick_score: Optional[float] = None


class DraftAdvice(BaseModel):
    """AI natural-language recommendation for the current pick."""
    recommended_player: Optional[str] = None
    alternatives: List[str] = []
    reasoning: str = ""
    strategy_note: str = ""


class DraftAssistResponse(BaseModel):
    """Live draft assistant response."""
    draft_id: str
    status: Optional[str] = None
    round: Optional[int] = None
    picks_made: int
    team_count: int
    scoring: str
    user_roster: List[Dict[str, Any]] = []
    user_position_counts: Dict[str, int] = {}
    recommendations: List[DraftPickRecommendation] = []
    ai_advice: Optional[DraftAdvice] = None
