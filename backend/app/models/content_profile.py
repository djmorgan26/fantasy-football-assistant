"""
League content profile: stores the "voice" of a fantasy league so AI-generated
content (roasts, power rankings, awards, season recaps) sounds like the group
instead of generic AI snark.

The corpus (humor_examples) and manager personas are filled in by the user over
time. The model works fine empty — the generator falls back to a sensible default
voice until real examples are provided.
"""
from sqlalchemy import Column, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base


class LeagueContentProfile(Base):
    __tablename__ = "league_content_profiles"

    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False, unique=True, index=True)

    # Free-text description of the group's tone, humor, and inside jokes.
    voice_guide = Column(Text, nullable=True)

    # The corpus: a list of past write-ups used as few-shot style anchors.
    # Each item: {"title": str, "text": str, "year": optional int}
    humor_examples = Column(JSON, nullable=True, default=list)

    # Per-manager personas used to make content personal.
    # Each item: {"name": str, "team_name": str, "notes": str, "bits": [str]}
    personas = Column(JSON, nullable=True, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
