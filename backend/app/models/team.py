from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    espn_team_id = Column(Integer, nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    
    # Team details
    name = Column(String(255), nullable=False)
    location = Column(String(255))
    nickname = Column(String(255))
    abbreviation = Column(String(10))
    logo_url = Column(String(500), nullable=True)
    
    # Performance metrics
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)
    points_for = Column(Float, default=0.0)
    points_against = Column(Float, default=0.0)
    
    # Current roster (JSON array of player IDs with positions)
    current_roster = Column(JSON, nullable=True)
    
    # Owner relationship
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    league = relationship("League", back_populates="teams")
    owner = relationship("User", back_populates="teams", foreign_keys=[owner_user_id])
    trades_proposed = relationship("Trade", back_populates="proposing_team", foreign_keys="Trade.proposing_team_id")
    trades_received = relationship("Trade", back_populates="receiving_team", foreign_keys="Trade.receiving_team_id")

    # Unique constraint for ESPN team ID within a league
    __table_args__ = (
        {"extend_existing": True}
    )