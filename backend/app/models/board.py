"""
The league content board, and the voice corpus it feeds.

This is the social surface: members post, the league reacts, and the posts that
land become the style anchors the AI writes from. The AI's own output posts here
too, under the same rules, so reactions to a weekly roast are training signal
rather than a dead end.

Reactions are typed, not a like/dislike binary. A binary records *that* a post
landed; the five kinds below record *how*, which is the part a voice profile can
actually learn from.
"""
import enum

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Enum, ForeignKey, Index,
    Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class ReactionKind(str, enum.Enum):
    SAVAGE = "savage"
    FUNNY = "funny"
    BRUTAL = "brutal"
    SMART = "smart"
    COLD = "cold"


# How much each reaction moves a post's score. Positive kinds are not equal:
# "savage" and "funny" are what this league is for, so they carry most weight.
# "cold" is the only negative, and it is what stops a flat recap being mined as
# a style example.
REACTION_WEIGHTS = {
    ReactionKind.SAVAGE: 3,
    ReactionKind.FUNNY: 3,
    ReactionKind.BRUTAL: 2,
    ReactionKind.SMART: 2,
    ReactionKind.COLD: -2,
}

# A reply is the strongest evidence a post landed — it cost somebody effort.
COMMENT_WEIGHT = 2


class PostKind(str, enum.Enum):
    POST = "post"                      # a human wrote it
    WEEKLY_RECAP = "weekly_recap"
    POWER_RANKINGS = "power_rankings"
    AWARDS = "awards"
    TRASH_TALK = "trash_talk"
    SEASON_RECAP = "season_recap"
    DIGEST = "digest"                  # the league news digest


class BoardPost(Base):
    __tablename__ = "board_posts"

    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, index=True)

    # NULL means the AI wrote it. The board treats those posts identically;
    # only the byline and the generated_by field differ.
    author_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    kind = Column(Enum(PostKind, native_enum=False, length=32), nullable=False, default=PostKind.POST)
    title = Column(String(300), nullable=True)
    body = Column(Text, nullable=False)

    # Storage keys, not bytes. Supabase Storage in production.
    media_paths = Column(JSON, nullable=False, default=list)

    week = Column(Integer, nullable=True)

    # Which model wrote it: a Groq model id, or "fallback". NULL for humans.
    generated_by = Column(String(120), nullable=True)

    # A member can keep a post out of the voice corpus. One boolean now beats
    # an unpleasant retrofit once there is a season of posts to go back through.
    allow_training = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    author = relationship("User", lazy="selectin")
    comments = relationship(
        "BoardComment", back_populates="post", cascade="all, delete-orphan", lazy="selectin"
    )
    reactions = relationship(
        "BoardReaction", back_populates="post", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_board_posts_league_created", "league_id", "created_at"),
    )

    @property
    def is_ai(self) -> bool:
        return self.author_user_id is None


class BoardComment(Base):
    __tablename__ = "board_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("board_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("board_comments.id", ondelete="CASCADE"), nullable=True)
    author_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    post = relationship("BoardPost", back_populates="comments")
    author = relationship("User", lazy="selectin")


class BoardReaction(Base):
    __tablename__ = "board_reactions"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("board_posts.id", ondelete="CASCADE"), nullable=True, index=True)
    comment_id = Column(Integer, ForeignKey("board_comments.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reaction = Column(Enum(ReactionKind, native_enum=False, length=16), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("BoardPost", back_populates="reactions")

    __table_args__ = (
        # Exactly one target: a reaction belongs to a post or a comment.
        CheckConstraint(
            "(post_id IS NOT NULL AND comment_id IS NULL) OR "
            "(post_id IS NULL AND comment_id IS NOT NULL)",
            name="ck_board_reactions_one_target",
        ),
        # One of each kind per person per thing. Tapping 🔥 twice is a toggle,
        # not a second vote.
        UniqueConstraint("user_id", "post_id", "reaction", name="uq_board_reaction_post"),
        UniqueConstraint("user_id", "comment_id", "reaction", name="uq_board_reaction_comment"),
    )


class VoiceSample(Base):
    """A piece of writing this league rated highly, kept as a style anchor.

    These replace the hand-typed `humor_examples` on LeagueContentProfile: same
    role in the prompt, but harvested from what the league actually laughed at
    rather than from whatever somebody remembered to paste into a settings form.
    """
    __tablename__ = "voice_samples"

    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, index=True)
    source_post_id = Column(Integer, ForeignKey("board_posts.id", ondelete="SET NULL"), nullable=True)
    author_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    title = Column(String(300), nullable=True)
    text = Column(Text, nullable=False)

    # The board score at harvest time; the corpus is ordered by it.
    score = Column(Integer, nullable=False, default=0)

    # Which reactions it drew, e.g. ["savage", "funny"]. Lets a generator ask
    # for anchors that match the tone it is aiming at.
    tags = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_voice_samples_league_score", "league_id", "score"),
    )
