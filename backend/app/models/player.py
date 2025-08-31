from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Float, Text
from sqlalchemy.sql import func
from app.db.database import Base


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    espn_player_id = Column(Integer, unique=True, nullable=False, index=True)
    
    # Player basic info
    full_name = Column(String(255), nullable=False)
    first_name = Column(String(255))
    last_name = Column(String(255))
    
    # Position and team info
    position_id = Column(Integer, nullable=False)  # ESPN position ID
    position_name = Column(String(10))  # QB, RB, WR, TE, K, D/ST
    pro_team_id = Column(Integer)  # NFL team ID
    pro_team_abbr = Column(String(10))  # NFL team abbreviation
    
    # Eligibility
    eligible_slots = Column(JSON)  # Array of eligible lineup slot IDs
    
    # Player status
    is_active = Column(Boolean, default=True)
    injury_status = Column(String(50), nullable=True)  # ACTIVE, QUESTIONABLE, DOUBTFUL, OUT, IR
    
    # Current season stats (JSON object)
    season_stats = Column(JSON, nullable=True)
    
    # Recent performance data
    last_week_points = Column(Float, default=0.0)
    season_points = Column(Float, default=0.0)
    average_points = Column(Float, default=0.0)
    
    # News and updates
    latest_news = Column(Text, nullable=True)
    news_updated = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_synced = Column(DateTime(timezone=True), nullable=True)