from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Encrypted ESPN credentials
    espn_s2_encrypted = Column(Text, nullable=True)
    espn_swid_encrypted = Column(Text, nullable=True)

    # Relationships
    owned_leagues = relationship("League", back_populates="owner", foreign_keys="League.owner_user_id")
    teams = relationship("Team", back_populates="owner", foreign_keys="Team.owner_user_id")
    trades = relationship("Trade", back_populates="user", foreign_keys="Trade.user_id")