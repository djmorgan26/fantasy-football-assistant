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
from app.services.espn_service import ESPNCookies, ESPNError, ESPNService
from app.services.llm_service import llm_service
from app.utils.encryption import ESPNCredentialManager
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


def _ensure_supported(league: League) -> None:
    """Both Sleeper and ESPN leagues are supported, as long as they're connected."""
    if league.platform == PlatformType.SLEEPER and league.sleeper_league_id:
        return
    if league.platform == PlatformType.ESPN and league.espn_league_id:
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="This league isn't connected to a supported platform yet.",
    )


def _espn_cookies(league: League) -> ESPNCookies | None:
    """Build ESPN auth cookies from the league's stored encrypted credentials."""
    s2 = ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None
    swid = ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
    if s2 or swid:
        return ESPNCookies(espn_s2=s2, swid=swid)
    return None


async def _fetch_narrative(league: League, week: int) -> dict:
    if league.platform == PlatformType.SLEEPER:
        return await content_service.get_weekly_narrative(league.sleeper_league_id, week)
    return await content_service.get_weekly_narrative_espn(
        str(league.espn_league_id), week, _espn_cookies(league)
    )


async def _fetch_owner_pairs(league: League, season: int | None = None) -> list:
    """[{team_name, owner_name}] for a league, used to auto-seed personas."""
    if league.platform == PlatformType.SLEEPER:
        users = await content_service.sleeper.get_league_users(league.sleeper_league_id)
        pairs = []
        for u in users:
            owner = u.get("display_name") or "Unknown Manager"
            team = (u.get("metadata") or {}).get("team_name") or owner
            pairs.append({"team_name": team, "owner_name": owner})
        return pairs
    espn = ESPNService()
    return await espn.get_team_owner_pairs(
        str(league.espn_league_id), _espn_cookies(league), season=season
    )


async def _fetch_standings(league: League) -> list:
    if league.platform == PlatformType.SLEEPER:
        return await content_service.get_standings(league.sleeper_league_id)
    return await content_service.get_standings_espn(str(league.espn_league_id), _espn_cookies(league))


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


@router.post("/{league_id}/personas/auto-fill", response_model=ContentProfileResponse)
async def autofill_personas(
    league_id: int,
    season: int | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """
    Auto-seed the league's manager personas from real team names + owners.

    Pulls teams from the connected platform (ESPN or Sleeper) so you don't have
    to type them all in. Existing persona notes/bits are preserved for managers
    that are already in the profile; voice_guide and humor_examples are untouched.
    For ESPN you can pass ?season=<year> to read a past season's rosters.
    """
    league = await _load_league(league_id, current_user, db)
    _ensure_supported(league)

    try:
        pairs = await _fetch_owner_pairs(league, season)
    except (SleeperError, ESPNError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch league rosters: {str(e)}",
        )

    profile = await _get_profile(league_id, db)
    existing = {p.get("name"): p for p in (profile.personas if profile and profile.personas else [])}

    personas = []
    for pair in pairs:
        owner = pair["owner_name"]
        team = pair["team_name"]
        prev = existing.get(owner) or {}
        personas.append({
            "name": owner,
            "team_name": team,
            "notes": prev.get("notes") or f"Manager of {team}.",
            "bits": prev.get("bits") or [],
        })

    if profile is None:
        profile = LeagueContentProfile(
            league_id=league_id,
            voice_guide=None,
            humor_examples=[],
            personas=personas,
        )
        db.add(profile)
    else:
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
    """Get the data-driven story facts for a week (no AI). Works for ESPN and Sleeper."""
    league = await _load_league(league_id, current_user, db)
    _ensure_supported(league)
    try:
        return await _fetch_narrative(league, week)
    except (SleeperError, ESPNError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch league data: {str(e)}",
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
    _ensure_supported(league)

    profile = _profile_dict(await _get_profile(league_id, db))
    week = payload.week or max((league.current_week or 1) - 1, 1)

    try:
        narrative = None
        standings = None
        # Weekly pieces need the week's facts; season recap needs standings.
        if payload.content_type in ("weekly_recap", "power_rankings", "awards"):
            narrative = await _fetch_narrative(league, week)
        if payload.content_type in ("power_rankings", "season_recap"):
            standings = await _fetch_standings(league)

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
    except (SleeperError, ESPNError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch league data: {str(e)}",
        )


@router.get("/health")
async def content_health():
    return {
        "content_engine": "ready",
        "llm_available": llm_service.is_available(),
        "content_types": list(CONTENT_TYPES),
    }
