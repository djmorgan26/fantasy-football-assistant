"""Who, besides the owner, is allowed inside a league.

A platform league is one row in `leagues`, shared by everyone in it. Before
this table there was only `owner_user_id`, and the connect endpoints reassigned
it to whoever had connected the league most recently: the second manager to
link the same ESPN or Sleeper league silently took it from the first, who then
got "League not found or access denied" on every page, board included.

Membership is what makes the board work as designed. The whole point is that a
league's managers post to the same board, so they have to resolve to the same
league row.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.database import Base


class LeagueMember(Base):
    __tablename__ = "league_members"
    __table_args__ = (
        UniqueConstraint("league_id", "user_id", name="uq_league_members_league_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # "owner" is the manager who connected it first; everyone else is "member".
    # Nothing branches on this yet, but the board will need it to decide who can
    # delete someone else's post.
    role = Column(String(32), nullable=False, default="member")

    # This manager's own Sleeper account. The league row carries one
    # `sleeper_user_id`, which is only ever right for one person in it; draft
    # recommendations need the id of whoever is asking.
    sleeper_user_id = Column(String(255), nullable=True)

    # The team this manager runs. It lives here rather than on
    # `Team.owner_user_id` because that column holds one user, so two people who
    # co-own a team (common in a real league) fought over it: the second to
    # claim silently unclaimed the first, and their roster vanished.
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
