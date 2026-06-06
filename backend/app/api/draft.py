"""
API endpoints for draft preparation and the live draft assistant.

Provides a league-scoring-aware value board (VBD rankings) and live pick
recommendations driven by the free Sleeper draft API.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import structlog

from app.db.database import get_database
from app.models.user import User
from app.models.league import League, PlatformType
from app.core.auth import get_current_active_user
from app.core.config import settings
from app.services.sleeper_service import SleeperService, SleeperError
from app.services.draft_service import draft_service
from app.services.llm_service import llm_service
from app.schemas.draft import ValueBoardResponse, DraftAssistResponse, DraftAdvice

logger = structlog.get_logger()
router = APIRouter(prefix="/draft", tags=["draft"])


async def _load_sleeper_league(league_id: int, user: User, db: AsyncSession) -> League:
    """Load a Sleeper league owned by the user, or raise an HTTP error."""
    result = await db.execute(
        select(League).where(
            League.id == league_id,
            League.owner_user_id == user.id,
        )
    )
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found or access denied",
        )
    if league.platform != PlatformType.SLEEPER or not league.sleeper_league_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft tools currently support Sleeper leagues only.",
        )
    return league


@router.get("/rankings", response_model=ValueBoardResponse)
async def get_generic_rankings(
    scoring_type: str = Query("ppr", description="standard | half_ppr | ppr"),
    team_count: int = Query(12, ge=4, le=20),
    season: Optional[int] = Query(None, description="Defaults to configured season year"),
    limit: int = Query(200, ge=10, le=500),
    current_user: User = Depends(get_current_active_user),
):
    """
    Pre-draft cheat sheet: a VBD value board using standard scoring presets.

    Use this before connecting a league, or for a quick generic ranking. For a
    board tuned to your league's exact scoring, use /draft/value-board/{league_id}.
    """
    try:
        board = await draft_service.build_value_board(
            season=season or settings.espn_season_year,
            scoring_settings=None,
            scoring_type=scoring_type,
            roster_positions=None,
            team_count=team_count,
            limit=limit,
        )
        return board
    except SleeperError as e:
        logger.error("Sleeper error building rankings", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch player data from Sleeper: {str(e)}",
        )


@router.get("/value-board/{league_id}", response_model=ValueBoardResponse)
async def get_league_value_board(
    league_id: int,
    limit: int = Query(200, ge=10, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """
    Build a draft value board tuned to a league's EXACT scoring settings.

    Pulls live scoring + roster settings from Sleeper so projections and VBD
    reflect how your league actually awards points.
    """
    league = await _load_sleeper_league(league_id, current_user, db)
    sleeper = SleeperService()

    try:
        sleeper_league = await sleeper.get_league(league.sleeper_league_id)
    except SleeperError as e:
        logger.error("Sleeper error fetching league", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch league from Sleeper: {str(e)}",
        )

    season = int(sleeper_league.get("season") or league.season_year or settings.espn_season_year)
    scoring_settings = sleeper_league.get("scoring_settings")
    roster_positions = sleeper_league.get("roster_positions")
    team_count = sleeper_league.get("total_rosters") or league.size or 12

    try:
        board = await draft_service.build_value_board(
            season=season,
            scoring_settings=scoring_settings,
            scoring_type=league.scoring_type or "ppr",
            roster_positions=roster_positions,
            team_count=team_count,
            limit=limit,
        )
        return board
    except SleeperError as e:
        logger.error("Sleeper error building value board", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch player data from Sleeper: {str(e)}",
        )


@router.get("/assist/{league_id}", response_model=DraftAssistResponse)
async def get_draft_assist(
    league_id: int,
    ai: bool = Query(False, description="Include AI advice (slower; use on demand, not for polling)"),
    limit: int = Query(10, ge=1, le=30),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database),
):
    """
    Live draft assistant: best-available recommendations for the league's draft.

    Reads picks already made, infers your roster needs, and ranks undrafted
    players by value + positional need. Works for live and mock drafts.
    """
    league = await _load_sleeper_league(league_id, current_user, db)
    sleeper = SleeperService()

    try:
        sleeper_league = await sleeper.get_league(league.sleeper_league_id)
        drafts = await sleeper.get_league_drafts(league.sleeper_league_id)
    except SleeperError as e:
        logger.error("Sleeper error fetching draft info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch draft info from Sleeper: {str(e)}",
        )

    if not drafts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No draft found for this league yet.",
        )

    draft_id = drafts[0].get("draft_id")
    scoring_settings = sleeper_league.get("scoring_settings")
    roster_positions = sleeper_league.get("roster_positions")

    try:
        result = await draft_service.recommend_picks(
            draft_id=draft_id,
            user_id=league.sleeper_user_id,
            scoring_settings=scoring_settings,
            scoring_type=league.scoring_type or "ppr",
            roster_positions=roster_positions,
            limit=limit,
        )
    except SleeperError as e:
        logger.error("Sleeper error generating recommendations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not generate recommendations: {str(e)}",
        )

    # Optional AI narrative advice layered on top of the deterministic ranking
    if ai:
        advice = await llm_service.analyze_draft_pick(
            round_number=result.get("round") or 1,
            user_roster=result.get("user_roster", []),
            position_needs=result.get("user_position_counts", {}),
            top_available=result.get("recommendations", []),
            scoring=result.get("scoring", "ppr"),
        )
        result["ai_advice"] = DraftAdvice(**advice)

    return result


@router.get("/health")
async def draft_health():
    """Check that draft data sources are reachable."""
    return {
        "draft_tools": "ready",
        "llm_available": llm_service.is_available(),
        "data_source": "sleeper",
    }
