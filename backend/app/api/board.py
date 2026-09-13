"""
The league content board: posts, threaded comments, typed reactions.

Access is league-scoped. In production this sits behind Supabase row-level
security as well, but the API enforces it too so the rule holds wherever the
database happens to live.
"""
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.db.database import get_database
from app.models.board import (
    BoardComment,
    BoardPost,
    BoardReaction,
    ReactionKind,
    VoiceSample,
)
from app.models.league import League
from app.models.user import User
from app.schemas.board import (
    BoardStatsResponse,
    CommentCreate,
    CommentResponse,
    PostCreate,
    PostResponse,
    PostUpdate,
    ReactionRequest,
    VoiceSampleResponse,
)
from app.services import board_service

logger = structlog.get_logger()
router = APIRouter(prefix="/board", tags=["board"])


async def _league_or_404(league_id: int, user: User, db: AsyncSession) -> League:
    """The board is private to a league; everything here goes through this."""
    result = await db.execute(
        select(League).where(League.id == league_id, League.owner_user_id == user.id)
    )
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found or access denied",
        )
    return league


@router.get("/{league_id}/posts", response_model=List[PostResponse])
async def list_posts(
    league_id: int,
    sort: str = Query("new", pattern="^(new|top)$"),
    kind: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    await _league_or_404(league_id, current_user, db)
    return await board_service.load_feed(
        db, league_id, viewer_id=current_user.id, sort=sort, kind=kind, limit=limit
    )


@router.post("/{league_id}/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    league_id: int,
    payload: PostCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    await _league_or_404(league_id, current_user, db)

    post = BoardPost(
        league_id=league_id,
        author_user_id=current_user.id,
        kind=payload.kind,
        title=payload.title,
        body=payload.body,
        week=payload.week,
        media_paths=payload.media_paths,
        allow_training=payload.allow_training,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    loaded = await board_service.load_post(db, post.id, league_id)
    return board_service.serialize_post(loaded, viewer_id=current_user.id)


@router.patch("/{league_id}/posts/{post_id}", response_model=PostResponse)
async def update_post(
    league_id: int,
    post_id: int,
    payload: PostUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    await _league_or_404(league_id, current_user, db)
    post = await board_service.load_post(db, post_id, league_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # You can edit your own words. Opting an AI post out of training is fair
    # game for anyone in the league, since it is nobody's writing.
    is_author = post.author_user_id == current_user.id
    if not is_author and post.author_user_id is not None:
        raise HTTPException(status_code=403, detail="You can only edit your own posts")

    if payload.body is not None and is_author:
        post.body = payload.body
    if payload.title is not None and is_author:
        post.title = payload.title
    if payload.allow_training is not None:
        post.allow_training = payload.allow_training

    await db.commit()
    await board_service.refresh_voice_samples(db, league_id)

    loaded = await board_service.load_post(db, post_id, league_id)
    return board_service.serialize_post(loaded, viewer_id=current_user.id)


@router.delete("/{league_id}/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    league_id: int,
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    await _league_or_404(league_id, current_user, db)
    post = await board_service.load_post(db, post_id, league_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_user_id is not None and post.author_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own posts")

    await db.delete(post)
    await db.commit()
    await board_service.refresh_voice_samples(db, league_id)


@router.post("/{league_id}/posts/{post_id}/comments", response_model=CommentResponse,
             status_code=status.HTTP_201_CREATED)
async def add_comment(
    league_id: int,
    post_id: int,
    payload: CommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    await _league_or_404(league_id, current_user, db)
    post = await board_service.load_post(db, post_id, league_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comment = BoardComment(
        post_id=post_id,
        parent_id=payload.parent_id,
        author_user_id=current_user.id,
        body=payload.body,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    # A comment moves the post's score, which can move it in or out of the corpus.
    await board_service.refresh_voice_samples(db, league_id)

    comment.author = current_user
    return board_service.serialize_comment(comment, viewer_id=current_user.id)


@router.delete("/{league_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    league_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    await _league_or_404(league_id, current_user, db)
    comment = await db.get(BoardComment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own comments")

    await db.delete(comment)
    await db.commit()
    await board_service.refresh_voice_samples(db, league_id)


@router.post("/{league_id}/posts/{post_id}/reactions", response_model=PostResponse)
async def toggle_reaction(
    league_id: int,
    post_id: int,
    payload: ReactionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Tap once to react, tap the same one again to take it back."""
    await _league_or_404(league_id, current_user, db)
    post = await board_service.load_post(db, post_id, league_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = (
        await db.execute(
            select(BoardReaction).where(
                BoardReaction.post_id == post_id,
                BoardReaction.user_id == current_user.id,
                BoardReaction.reaction == payload.reaction,
            )
        )
    ).scalar_one_or_none()

    if existing:
        await db.delete(existing)
    else:
        db.add(BoardReaction(
            post_id=post_id,
            user_id=current_user.id,
            reaction=payload.reaction,
        ))
    await db.commit()

    await board_service.refresh_voice_samples(db, league_id)

    loaded = await board_service.load_post(db, post_id, league_id)
    return board_service.serialize_post(loaded, viewer_id=current_user.id)


@router.get("/{league_id}/voice-samples", response_model=List[VoiceSampleResponse])
async def list_voice_samples(
    league_id: int,
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """What the AI is currently learning this league's voice from.

    Worth exposing: a league that can see which of its posts are teaching the
    model understands immediately why reacting to things matters.
    """
    await _league_or_404(league_id, current_user, db)

    rows = (
        await db.execute(
            select(VoiceSample)
            .where(VoiceSample.league_id == league_id)
            .order_by(VoiceSample.score.desc(), VoiceSample.id.desc())
            .limit(limit)
        )
    ).scalars().all()

    out = []
    for row in rows:
        author = await db.get(User, row.author_user_id) if row.author_user_id else None
        out.append({
            "id": row.id,
            "title": row.title,
            "text": row.text,
            "score": row.score,
            "tags": row.tags or [],
            "author_name": (
                (author.full_name or author.email.split("@")[0]) if author else "The Commissioner"
            ),
        })
    return out


@router.get("/{league_id}/stats", response_model=BoardStatsResponse)
async def board_stats(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    await _league_or_404(league_id, current_user, db)

    posts = (await db.execute(
        select(func.count(BoardPost.id)).where(BoardPost.league_id == league_id)
    )).scalar() or 0

    comments = (await db.execute(
        select(func.count(BoardComment.id))
        .select_from(BoardComment)
        .join(BoardPost, BoardPost.id == BoardComment.post_id)
        .where(BoardPost.league_id == league_id)
    )).scalar() or 0

    reaction_rows = (await db.execute(
        select(BoardReaction.reaction, func.count(BoardReaction.id))
        .select_from(BoardReaction)
        .join(BoardPost, BoardPost.id == BoardReaction.post_id)
        .where(BoardPost.league_id == league_id)
        .group_by(BoardReaction.reaction)
    )).all()

    samples = (await db.execute(
        select(func.count(VoiceSample.id)).where(VoiceSample.league_id == league_id)
    )).scalar() or 0

    total_reactions = sum(n for _, n in reaction_rows)
    top = max(reaction_rows, key=lambda row: row[1])[0] if reaction_rows else None

    return {
        "posts": posts,
        "comments": comments,
        "reactions": total_reactions,
        "voice_samples": samples,
        "top_reaction": (top.value if isinstance(top, ReactionKind) else top) if top else None,
    }
