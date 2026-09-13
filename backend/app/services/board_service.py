"""
Scoring and harvesting for the content board.

Two jobs:

1. Turn posts + reactions + comments into a ranked feed.
2. Promote the posts a league rated highly into `voice_samples`, which is what
   the content generator reads as style anchors. That promotion is the whole
   point of the board: it replaces a settings form nobody fills in with a
   corpus the league builds by using the app.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.board import (
    COMMENT_WEIGHT,
    REACTION_WEIGHTS,
    BoardComment,
    BoardPost,
    BoardReaction,
    PostKind,
    ReactionKind,
    VoiceSample,
)
from app.models.user import User

logger = structlog.get_logger()

# A post has to clear this before it is worth learning from. Two people finding
# something funny is a signal; one person reacting to their own post is not.
VOICE_SAMPLE_MIN_SCORE = 4

# How many anchors the corpus keeps per league. The generator only ever shows
# the model three, but keeping a deeper bench lets it pick by tone.
VOICE_SAMPLE_LIMIT = 25

# Generated content types that belong on the board. A season recap is a
# once-a-year artifact and a digest posts itself, so both stay off this list.
BOARD_PUBLISHED_KINDS = ("weekly_recap", "power_rankings", "awards")

POST_TITLES = {
    "weekly_recap": "Weekly Roast",
    "power_rankings": "Power Rankings",
    "awards": "Weekly Awards",
    "season_recap": "Season Recap",
    "trash_talk": "Trash Talk",
    "digest": "League news digest",
    "post": "Post",
}

# Long posts make poor few-shot anchors — they eat the context window and the
# model starts copying their structure instead of their voice.
VOICE_SAMPLE_MAX_CHARS = 1200


def _expire(db: AsyncSession) -> None:
    """Force the next read to hit the database.

    Sessions here are built with `expire_on_commit=False`, so an object that
    was loaded before a commit keeps the relationship collections it had at
    load time. A post read, then reacted to, then read again inside one request
    would otherwise come back with its old reactions and score 0.
    """
    db.expire_all()


def score_post(post: BoardPost) -> int:
    """Weighted reactions plus comment volume."""
    total = sum(REACTION_WEIGHTS.get(r.reaction, 0) for r in (post.reactions or []))
    return total + COMMENT_WEIGHT * len(post.comments or [])


def reaction_counts(post: BoardPost) -> Dict[str, int]:
    counts = {kind.value: 0 for kind in ReactionKind}
    for r in post.reactions or []:
        key = r.reaction.value if isinstance(r.reaction, ReactionKind) else str(r.reaction)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _author_label(user: Optional[User]) -> str:
    if user is None:
        return "The Commissioner"
    return user.full_name or (user.email or "").split("@")[0] or "Someone"


def serialize_comment(comment: BoardComment, *, viewer_id: int) -> dict:
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "parent_id": comment.parent_id,
        "body": comment.body,
        "author_id": comment.author_user_id,
        "author_name": _author_label(comment.author),
        "is_mine": comment.author_user_id == viewer_id,
        "created_at": comment.created_at,
    }


def serialize_post(post: BoardPost, *, viewer_id: int) -> dict:
    """One post, with everything the card renders — including what *you* reacted."""
    mine = {
        (r.reaction.value if isinstance(r.reaction, ReactionKind) else str(r.reaction))
        for r in (post.reactions or [])
        if r.user_id == viewer_id
    }
    comments = sorted(post.comments or [], key=lambda c: (c.created_at is None, c.created_at))

    return {
        "id": post.id,
        "league_id": post.league_id,
        "kind": post.kind.value if isinstance(post.kind, PostKind) else str(post.kind),
        "title": post.title,
        "body": post.body,
        "media_paths": post.media_paths or [],
        "week": post.week,
        "is_ai": post.author_user_id is None,
        "generated_by": post.generated_by,
        "allow_training": post.allow_training,
        "author_id": post.author_user_id,
        "author_name": _author_label(post.author),
        "is_mine": post.author_user_id is not None and post.author_user_id == viewer_id,
        "score": score_post(post),
        "reactions": reaction_counts(post),
        "my_reactions": sorted(mine),
        "comment_count": len(post.comments or []),
        "comments": [serialize_comment(c, viewer_id=viewer_id) for c in comments],
        "created_at": post.created_at,
    }


async def load_feed(
    db: AsyncSession,
    league_id: int,
    *,
    viewer_id: int,
    sort: str = "new",
    kind: Optional[str] = None,
    limit: int = 50,
) -> List[dict]:
    """The board, newest or best first."""
    _expire(db)
    stmt = select(BoardPost).where(BoardPost.league_id == league_id)
    if kind:
        stmt = stmt.where(BoardPost.kind == kind)
    stmt = stmt.order_by(BoardPost.created_at.desc()).limit(limit)

    posts = (await db.execute(stmt)).scalars().unique().all()
    serialized = [serialize_post(p, viewer_id=viewer_id) for p in posts]

    if sort == "top":
        serialized.sort(key=lambda p: (-p["score"], p["id"] * -1))
    return serialized


async def load_post(db: AsyncSession, post_id: int, league_id: int) -> Optional[BoardPost]:
    _expire(db)
    result = await db.execute(
        select(BoardPost).where(BoardPost.id == post_id, BoardPost.league_id == league_id)
    )
    return result.scalars().unique().one_or_none()


# --------------------------------------------------------------- harvesting

async def refresh_voice_samples(db: AsyncSession, league_id: int) -> int:
    """Rebuild this league's style corpus from its best-rated posts.

    Cheap enough to run after every reaction: a league has tens of posts, not
    millions. Rebuilding wholesale rather than incrementally means a post that
    later collects 🧊 reactions drops back out of the corpus on its own.
    """
    _expire(db)
    posts = (
        await db.execute(
            select(BoardPost).where(
                BoardPost.league_id == league_id,
                BoardPost.allow_training.is_(True),
            )
        )
    ).scalars().unique().all()

    scored = []
    for post in posts:
        score = score_post(post)
        if score < VOICE_SAMPLE_MIN_SCORE:
            continue
        text = (post.body or "").strip()
        if len(text) < 40:          # one-liners teach the model nothing
            continue
        scored.append((score, post, text[:VOICE_SAMPLE_MAX_CHARS]))

    scored.sort(key=lambda row: (-row[0], -row[1].id))
    keep = scored[:VOICE_SAMPLE_LIMIT]

    # Wholesale rebuild: simplest thing that stays correct when scores move.
    await db.execute(delete(VoiceSample).where(VoiceSample.league_id == league_id))

    for score, post, text in keep:
        counts = reaction_counts(post)
        tags = [kind for kind, n in counts.items() if n > 0 and kind != ReactionKind.COLD.value]
        db.add(VoiceSample(
            league_id=league_id,
            source_post_id=post.id,
            author_user_id=post.author_user_id,
            title=post.title,
            text=text,
            score=score,
            tags=tags,
        ))

    await db.commit()
    logger.info("Voice corpus refreshed", league_id=league_id, samples=len(keep))
    return len(keep)


async def get_voice_examples(db: AsyncSession, league_id: int, limit: int = 3) -> List[dict]:
    """The top style anchors, in the shape `_voice_block()` already expects."""
    rows = (
        await db.execute(
            select(VoiceSample)
            .where(VoiceSample.league_id == league_id)
            .order_by(VoiceSample.score.desc(), VoiceSample.id.desc())
            .limit(limit)
        )
    ).scalars().all()

    return [
        {"title": row.title or "A post this league liked", "text": row.text, "score": row.score}
        for row in rows
    ]


async def get_author_voices(db: AsyncSession, league_id: int, limit_per_author: int = 2) -> List[dict]:
    """How each member writes, drawn from their own best posts.

    Feeds the persona block so the generator can write *about* someone in terms
    they would recognise, or *as* them when asked.
    """
    rows = (
        await db.execute(
            select(VoiceSample)
            .where(VoiceSample.league_id == league_id, VoiceSample.author_user_id.isnot(None))
            .order_by(VoiceSample.score.desc())
        )
    ).scalars().all()

    by_author: Dict[int, List[VoiceSample]] = {}
    for row in rows:
        by_author.setdefault(row.author_user_id, []).append(row)

    out = []
    for author_id, samples in by_author.items():
        user = await db.get(User, author_id)
        out.append({
            "user_id": author_id,
            "name": _author_label(user),
            "samples": [s.text for s in samples[:limit_per_author]],
        })
    return out


async def publish_ai_post(
    db: AsyncSession,
    *,
    league_id: int,
    kind: str,
    body: str,
    title: Optional[str] = None,
    week: Optional[int] = None,
    generated_by: Optional[str] = None,
) -> BoardPost:
    """Put a generated piece on the board so the league can rate it.

    This is the other half of the loop. Without it the AI never finds out
    whether anything it wrote landed.
    """
    post = BoardPost(
        league_id=league_id,
        author_user_id=None,
        kind=kind,
        title=title,
        body=body,
        week=week,
        generated_by=generated_by,
        media_paths=[],
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    logger.info("AI post published to board", league_id=league_id, kind=kind, post_id=post.id)
    return post
