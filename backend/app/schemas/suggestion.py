"""
Pydantic schemas for strategic suggestions
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal


class SuggestionResponse(BaseModel):
    """Strategic suggestion response"""
    id: str
    type: Literal["pickup", "drop", "trade", "lineup"]
    priority: Literal["high", "medium", "low"]
    title: str
    description: str
    reasoning: str
    potential_impact: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    action_details: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
