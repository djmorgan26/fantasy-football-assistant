"""
News, live scores and waiver buzz — plus the one thing a national fantasy site
structurally cannot build: a wire filtered to *your league's* rosters.

FantasyPros knows your roster. They do not know your eleven opponents'. We do,
so "Tua is out" can become "Tua is out, which is Brad's problem, and he plays
you Sunday."
"""
import asyncio
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.db.database import get_database
from app.models.league import League, PlatformType
from app.models.team import Team
from app.models.user import User
from app.services import board_service, league_context, news_service
from app.services.llm_service import llm_service

logger = structlog.get_logger()
router = APIRouter(prefix="/news", tags=["news"])


@router.get("/wire")
async def nfl_wire(
    limit: int = Query(30, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
):
    """The raw NFL news wire, unfiltered."""
    return {"articles": await news_service.fetch_news(limit=limit)}


@router.get("/scoreboard")
async def scoreboard(current_user: User = Depends(get_current_active_user)):
    """Today's games, for the live ticker."""
    return {"games": await news_service.fetch_scoreboard()}


@router.get("/trending")
async def trending(
    kind: str = Query("add", pattern="^(add|drop)$"),
    hours: int = Query(24, ge=1, le=72),
    limit: int = Query(10, ge=1, le=25),
    current_user: User = Depends(get_current_active_user),
):
    """Waiver buzz from Sleeper's whole user base."""
    return {"players": await news_service.fetch_trending(kind=kind, hours=hours, limit=limit)}


@router.get("/league/{league_id}")
async def league_news(
    league_id: int,
    limit: int = Query(30, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """The wire, annotated with who in your league owns the player involved."""
    league = await league_context.load_league(league_id, current_user, db)

    articles, ownership = await asyncio.gather(
        news_service.fetch_news(limit=limit),
        league_context.roster_ownership(league, db),
    )

    annotated = []
    for article in articles:
        owner = news_service.relevant_to_roster(article, ownership)
        annotated.append({**article, "rostered_by": owner})

    # League-relevant news first; the rest still shows, just below.
    annotated.sort(key=lambda a: a["rostered_by"] is None)

    return {
        "articles": annotated,
        "rostered_count": sum(1 for a in annotated if a["rostered_by"]),
        "league_name": league.name,
    }


@router.get("/digest/{league_id}")
async def league_digest(
    league_id: int,
    publish: bool = Query(False, description="Also post the digest to the content board"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """One paragraph: what changed for *your* league today.

    Grounded the same way every other generated thing in this app is — the facts
    are gathered first and handed to the model, which is only allowed to write
    about what it was given.
    """
    league = await league_context.load_league(league_id, current_user, db)

    articles, ownership = await asyncio.gather(
        news_service.fetch_news(limit=40),
        league_context.roster_ownership(league, db),
    )

    relevant = []
    for article in articles:
        owner = news_service.relevant_to_roster(article, ownership)
        if owner:
            relevant.append({**article, "rostered_by": owner})

    if not relevant:
        return {
            "digest": "Nothing on the wire touches a roster in this league right now. Quiet day.",
            "generated_by": "none",
            "items": [],
        }

    facts = "\n".join(
        f"- {a['headline']} ({a['category']}) — rostered by {a['rostered_by']}. {a['description']}"
        for a in relevant[:10]
    )

    profile = await content_service_profile(db, league_id)
    voice = (profile or {}).get("voice_guide") or ""

    prompt = (
        f"League: {league.name}\n\n"
        f"TODAY'S NFL NEWS THAT TOUCHES THIS LEAGUE'S ROSTERS:\n{facts}\n\n"
        "Write a single tight paragraph (3-5 sentences) telling this league what changed "
        "today. Name the fantasy teams affected, because that is the whole point — these "
        "are the people they play against. Be direct and a little funny, never corporate.\n\n"
        "HARD RULES: use only the facts listed above. Refer to managers by their fantasy "
        "team name exactly as written above and never by a personal name — you do not know "
        "anyone's real name. Do not invent players, injuries, scores or people."
        + (f"\n\nLEAGUE VOICE:\n{voice}" if voice else "")
    )

    if not llm_service.is_available():
        digest = "Today's league-relevant news:\n" + "\n".join(
            f"• {a['headline']} — {a['rostered_by']}" for a in relevant[:6]
        )
        generated_by = "fallback"
    else:
        try:
            digest = await asyncio.to_thread(
                llm_service.complete,
                system=(
                    "You write a daily fantasy football briefing for one specific league. "
                    "You know every team in it. Be specific and brief."
                ),
                prompt=prompt,
                temperature=0.7,
                # Generous on purpose: the default Groq model reasons before it
                # answers and that reasoning is billed here. Too small a budget
                # does not shorten the digest, it returns nothing at all.
                max_tokens=1500,
                purpose="league_news_digest",
            )
            generated_by = llm_service.model
        except Exception as e:
            logger.error("Digest generation failed", error=str(e))
            digest = "Today's league-relevant news:\n" + "\n".join(
                f"• {a['headline']} — {a['rostered_by']}" for a in relevant[:6]
            )
            generated_by = "fallback"

    if publish:
        await board_service.publish_ai_post(
            db,
            league_id=league_id,
            kind="digest",
            title="League news digest",
            body=digest,
            generated_by=generated_by,
        )

    return {
        "digest": digest.strip(),
        "generated_by": generated_by,
        "items": relevant[:10],
    }


async def content_service_profile(db: AsyncSession, league_id: int) -> Optional[dict]:
    """The league's voice profile, if one has been set up."""
    from app.models.content_profile import LeagueContentProfile

    row = (
        await db.execute(
            select(LeagueContentProfile).where(LeagueContentProfile.league_id == league_id)
        )
    ).scalar_one_or_none()
    if not row:
        return None
    return {
        "voice_guide": row.voice_guide,
        "humor_examples": row.humor_examples or [],
        "personas": row.personas or [],
    }
