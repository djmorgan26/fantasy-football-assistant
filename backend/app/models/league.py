from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class League(Base):
    __tablename__ = "leagues"

    id = Column(Integer, primary_key=True, index=True)
    espn_league_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    season_year = Column(Integer, nullable=False)
    size = Column(Integer, nullable=False)
    
    # League settings
    scoring_type = Column(String(50), default="standard")  # standard, ppr, half_ppr
    roster_settings = Column(JSON, nullable=True)
    scoring_settings = Column(JSON, nullable=True)
    
    # ESPN authentication (encrypted)
    espn_s2_encrypted = Column(Text, nullable=True)
    espn_swid_encrypted = Column(Text, nullable=True)
    
    # League metadata
    current_week = Column(Integer, default=1)
    is_public = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # Owner relationship
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_synced = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="owned_leagues", foreign_keys=[owner_user_id])
    teams = relationship("Team", back_populates="league")
    trades = relationship("Trade", back_populates="league")