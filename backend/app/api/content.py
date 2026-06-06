"""
API endpoints for the content & humor engine.

- Manage a league's voice profile (tone, manager personas, past write-ups)
- Inspect the data-driven story facts for a week
- Generate league-personalized content (recap, power rankings, awards, season recap)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.db.database import get_database
from app.models.user import User
from app.models.league import League, PlatformType
from app.models.content_profile import LeagueContentProfile
from app.core.auth import get_current_active_user
from app.services.content_service import content_service, CONTENT_TYPES
from app.services.sleeper_service import SleeperError
from app.services.llm_service import llm_service
from app.schemas.content import (
    ContentProfileUpdate,
    ContentProfileResponse,
    GenerateContentRequest,
    GeneratedContentResponse,
    WeeklyNarrativeResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/content", tags=["content"])


async def _load_league(league_id: int, user: User, db: AsyncSession) -> League:
    result = await db.execute(
        select(League).where(League.id == league_id, League.owner_user_id == user.id)
    )
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="League not found or access denied")
    return league


async def _get_profile(league_id: int, db: AsyncSession) -> LeagueContentProfile:
    result = await db.execute(
        select(LeagueContentProfile).where(LeagueContentProfile.league_id == league_id)
    )
    return result.scalar_one_or_none()


def _profile_dict(profile: LeagueContentProfile) -> dict:
    if not profile:
        return {"voice_guide": None, "humor_examples": [], "personas": []}
    return {
        "voice_guide": profile.voice_guide,
        "humor_examples": profile.humor_examples or [],
        "personas": profile.personas or [],
    }


@router.get("/{league_id}/profile", response_model=ContentProfileResponse)
async def get_profile(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Get the league's voice profile (returns an empty profile if none set)."""
    await _load_league(league_id, current_user, db)
    profile = await _get_profile(league_id, db)
    data = _profile_dict(profile)
    return ContentProfileResponse(league_id=league_id, **data)


@router.put("/{league_id}/profile", response_model=ContentProfileResponse)
async def update_profile(
    league_id: int,
    payload: ContentProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Create or update the league's voice, personas, and past write-ups corpus."""
    await _load_league(league_id, current_user, db)
    profile = await _get_profile(league_id, db)

    humor = [e.model_dump() for e in payload.humor_examples]
    personas = [p.model_dump() for p in payload.personas]

    if profile is None:
        profile = LeagueContentProfile(
            league_id=league_id,
            voice_guide=payload.voice_guide,
            humor_examples=humor,
            personas=personas,
        )
        db.add(profile)
    else:
        profile.voice_guide = payload.voice_guide
        profile.humor_examples = humor
        profile.personas = personas

    await db.commit()
    await db.refresh(profile)
    return ContentProfileResponse(league_id=league_id, **_profile_dict(profile))


@router.get("/{league_id}/narrative/week/{week}", response_model=WeeklyNarrativeResponse)
async def get_weekly_narrative(
    league_id: int,
    week: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Get the data-driven story facts for a week (no AI)."""
    league = await _load_league(league_id, current_user, db)
    if league.platform != PlatformType.SLEEPER or not league.sleeper_league_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The content engine currently supports Sleeper leagues only.",
        )
    try:
        narrative = await content_service.get_weekly_narrative(league.sleeper_league_id, week)
        return narrative
    except SleeperError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch league data from Sleeper: {str(e)}",
        )


@router.post("/{league_id}/generate", response_model=GeneratedContentResponse)
async def generate_content(
    league_id: int,
    payload: GenerateContentRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """Generate league-personalized content from real data + the league's voice."""
    league = await _load_league(league_id, current_user, db)
    if league.platform != PlatformType.SLEEPER or not league.sleeper_league_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The content engine currently supports Sleeper leagues only.",
        )

    profile = _profile_dict(await _get_profile(league_id, db))
    week = payload.week or max((league.current_week or 1) - 1, 1)

    try:
        narrative = None
        standings = None
        # Weekly pieces need the week's facts; season recap needs standings.
        if payload.content_type in ("weekly_recap", "power_rankings", "awards"):
            narrative = await content_service.get_weekly_narrative(league.sleeper_league_id, week)
        if payload.content_type in ("power_rankings", "season_recap"):
            standings = await content_service.get_standings(league.sleeper_league_id)

        result = await content_service.generate(
            content_type=payload.content_type,
            league_name=league.name,
            week=week,
            profile=profile,
            narrative=narrative,
            standings=standings,
        )
        return GeneratedContentResponse(
            week=week,
            league_name=league.name,
            narrative=narrative,
            **result,
        )
    except SleeperError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch league data from Sleeper: {str(e)}",
        )


@router.get("/health")
async def content_health():
    return {
        "content_engine": "ready",
        "llm_available": llm_service.is_available(),
        "content_types": list(CONTENT_TYPES),
    }
