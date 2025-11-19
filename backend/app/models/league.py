from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum


class PlatformType(str, enum.Enum):
    """Supported fantasy football platforms"""
    ESPN = "espn"
    SLEEPER = "sleeper"


class League(Base):
    __tablename__ = "leagues"

    id = Column(Integer, primary_key=True, index=True)

    # Platform information
    platform = Column(Enum(PlatformType), nullable=False, default=PlatformType.ESPN, index=True)

    # Platform-specific IDs (only one should be populated based on platform)
    espn_league_id = Column(Integer, nullable=True, index=True)
    sleeper_league_id = Column(String(255), nullable=True, index=True)

    # Common league information
    name = Column(String(255), nullable=False)
    season_year = Column(Integer, nullable=False)
    size = Column(Integer, nullable=False)

    # League settings
    scoring_type = Column(String(50), default="standard")  # standard, ppr, half_ppr
    roster_settings = Column(JSON, nullable=True)
    scoring_settings = Column(JSON, nullable=True)

    # Platform-specific authentication/credentials (encrypted)
    # ESPN requires cookies for private leagues
    espn_s2_encrypted = Column(Text, nullable=True)
    espn_swid_encrypted = Column(Text, nullable=True)
    # Sleeper doesn't require auth but we store the user_id for reference
    sleeper_user_id = Column(String(255), nullable=True)

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
    matchups = relationship("Matchup", back_populates="league")
    waiver_budgets = relationship("WaiverBudget", back_populates="league")
    waiver_transactions = relationship("WaiverTransaction", back_populates="league")

    @property
    def platform_league_id(self) -> str:
        """Return the appropriate league ID based on platform"""
        if self.platform == PlatformType.ESPN:
            return str(self.espn_league_id) if self.espn_league_id else None
        elif self.platform == PlatformType.SLEEPER:
            return self.sleeper_league_id
        return None