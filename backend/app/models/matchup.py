from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Matchup(Base):
    __tablename__ = "matchups"

    id = Column(Integer, primary_key=True, index=True)
    matchup_id = Column(Integer, nullable=False)  # ESPN matchup ID
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    week = Column(Integer, nullable=False)
    
    # Teams in the matchup
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    
    # Scores
    home_score = Column(Float, default=0.0)
    away_score = Column(Float, default=0.0)
    
    # Matchup status
    is_playoff = Column(Boolean, default=False)
    winner = Column(String(50), default="UNDECIDED")  # "HOME", "AWAY", "TIE", "UNDECIDED"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    league = relationship("League", back_populates="matchups")
    home_team = relationship("Team", foreign_keys=[home_team_id], backref="home_matchups")
    away_team = relationship("Team", foreign_keys=[away_team_id], backref="away_matchups")

    # Unique constraint for matchup per league per week
    __table_args__ = (
        {"extend_existing": True}
    )