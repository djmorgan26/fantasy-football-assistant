from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class WaiverBudget(Base):
    __tablename__ = "waiver_budgets"

    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    
    # Budget information
    total_budget = Column(Float, default=100.0)  # Starting budget (usually $100)
    current_budget = Column(Float, default=100.0)  # Current available budget
    spent_budget = Column(Float, default=0.0)  # Total spent so far
    
    # Season tracking
    season_year = Column(Integer, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    league = relationship("League", back_populates="waiver_budgets")
    team = relationship("Team", back_populates="waiver_budget")

    # Unique constraint for one budget per team per league per season
    __table_args__ = (
        {"extend_existing": True}
    )


class WaiverTransaction(Base):
    __tablename__ = "waiver_transactions"

    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    
    # Transaction details
    player_id = Column(Integer, nullable=False)  # ESPN player ID
    player_name = Column(String(255), nullable=False)
    transaction_type = Column(String(50), nullable=False)  # "ADD", "DROP", "TRADE"
    bid_amount = Column(Float, default=0.0)  # Amount bid/spent
    
    # Transaction status
    status = Column(String(50), default="PENDING")  # "PENDING", "SUCCESSFUL", "FAILED"
    week = Column(Integer, nullable=False)
    
    # Additional details
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    league = relationship("League", back_populates="waiver_transactions")
    team = relationship("Team", back_populates="waiver_transactions")

    __table_args__ = (
        {"extend_existing": True}
    )