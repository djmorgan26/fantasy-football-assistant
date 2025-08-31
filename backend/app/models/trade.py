from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float, Text, Enum as SqlEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum


class TradeStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    
    # League and teams involved
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    proposing_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    receiving_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    
    # User who initiated the trade analysis
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Trade details
    proposed_players = Column(JSON, nullable=False)  # {"give": [player_ids], "receive": [player_ids]}
    status = Column(SqlEnum(TradeStatus), default=TradeStatus.PENDING)
    
    # Analysis results
    fairness_score = Column(Float, nullable=True)  # 0-100 fairness rating
    value_difference = Column(Float, nullable=True)  # Point value difference
    analysis_summary = Column(Text, nullable=True)  # AI-generated summary
    
    # ESPN trade details (if executed)
    espn_trade_id = Column(String(100), nullable=True)
    processed_date = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    league = relationship("League", back_populates="trades")
    proposing_team = relationship("Team", back_populates="trades_proposed", foreign_keys=[proposing_team_id])
    receiving_team = relationship("Team", back_populates="trades_received", foreign_keys=[receiving_team_id])
    user = relationship("User", back_populates="trades", foreign_keys=[user_id])