from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class WaiverBudgetBase(BaseModel):
    league_id: int
    team_id: int
    total_budget: float = 100.0
    current_budget: float = 100.0
    spent_budget: float = 0.0
    season_year: int


class WaiverBudgetCreate(WaiverBudgetBase):
    pass


class WaiverBudgetUpdate(BaseModel):
    current_budget: Optional[float] = None
    spent_budget: Optional[float] = None


class WaiverBudgetResponse(WaiverBudgetBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WaiverTransactionBase(BaseModel):
    league_id: int
    team_id: int
    player_id: int
    player_name: str
    transaction_type: str  # "ADD", "DROP", "TRADE"
    bid_amount: float = 0.0
    status: str = "PENDING"  # "PENDING", "SUCCESSFUL", "FAILED"
    week: int
    notes: Optional[str] = None


class WaiverTransactionCreate(WaiverTransactionBase):
    pass


class WaiverTransactionUpdate(BaseModel):
    status: Optional[str] = None
    bid_amount: Optional[float] = None
    notes: Optional[str] = None


class WaiverTransactionResponse(WaiverTransactionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TeamBudgetSummary(BaseModel):
    team_id: int
    team_name: str
    current_budget: float
    spent_budget: float
    total_budget: float
    recent_transactions: List[WaiverTransactionResponse]