from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    # Nullable: a user who only ever signs in with Google has no password.
    # Any code path that verifies a password must handle None (see
    # authenticate_user) rather than passing it to bcrypt, which raises.
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Google sign-in. We key on `sub`, Google's immutable per-account subject
    # id, not on email: a Google account can change its email address, and
    # matching on email would then either lose the link or, worse, hand the
    # account to whoever inherits the old address.
    google_sub = Column(String(255), unique=True, index=True, nullable=True)
    avatar_url = Column(Text, nullable=True)

    # Encrypted ESPN credentials
    espn_s2_encrypted = Column(Text, nullable=True)
    espn_swid_encrypted = Column(Text, nullable=True)

    # Yahoo access tokens are short-lived. Refresh tokens stay server-side and
    # are encrypted with the same application key as ESPN private-league data.
    yahoo_access_token_encrypted = Column(Text, nullable=True)
    yahoo_refresh_token_encrypted = Column(Text, nullable=True)
    yahoo_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    yahoo_guid = Column(String(255), nullable=True)

    # Relationships
    owned_leagues = relationship("League", back_populates="owner", foreign_keys="League.owner_user_id")
    teams = relationship("Team", back_populates="owner", foreign_keys="Team.owner_user_id")
    trades = relationship("Trade", back_populates="user", foreign_keys="Trade.user_id")
