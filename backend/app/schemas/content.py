"""
Pydantic schemas for the content & humor engine.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal


class HumorExample(BaseModel):
    """A past write-up used as a style anchor (the corpus)."""
    title: Optional[str] = None
    text: str
    year: Optional[int] = None


class ManagerPersona(BaseModel):
    """A league member's personality used to make content personal."""
    name: str
    team_name: Optional[str] = None
    notes: Optional[str] = None
    bits: List[str] = []


class ContentProfileUpdate(BaseModel):
    """Editable league voice profile."""
    voice_guide: Optional[str] = None
    humor_examples: List[HumorExample] = []
    personas: List[ManagerPersona] = []


class ContentProfileResponse(ContentProfileUpdate):
    league_id: int

    class Config:
        from_attributes = True


class GenerateContentRequest(BaseModel):
    content_type: Literal["weekly_recap", "power_rankings", "awards", "season_recap"]
    week: Optional[int] = None


class GeneratedContentResponse(BaseModel):
    content: str
    content_type: str
    generated_by: str
    week: Optional[int] = None
    league_name: Optional[str] = None
    narrative: Optional[Dict[str, Any]] = None


class WeeklyNarrativeResponse(BaseModel):
    """Structured, data-driven story facts for a week (no AI)."""
    week: int
    team_count: int
    median_score: float
    average_score: float
    highest_scorer: Optional[Dict[str, Any]] = None
    lowest_scorer: Optional[Dict[str, Any]] = None
    biggest_blowout: Optional[Dict[str, Any]] = None
    closest_game: Optional[Dict[str, Any]] = None
    lucky_wins: List[Dict[str, Any]] = []
    unlucky_losses: List[Dict[str, Any]] = []
    bench_blunder: Optional[Dict[str, Any]] = None
    results: List[Dict[str, Any]] = []
    teams: List[Dict[str, Any]] = []
