"""
API endpoints for AI-powered strategic suggestions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.database import get_database
from app.models.user import User
from app.models.league import League
from app.core.auth import get_current_active_user
from app.services.espn_service import ESPNService, ESPNCookies, ESPNError
from app.services.llm_service import llm_service
from app.utils.encryption import ESPNCredentialManager
from app.schemas.suggestion import SuggestionResponse
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.get("/{league_id}/{team_id}", response_model=List[SuggestionResponse])
async def get_strategic_suggestions(
    league_id: int,
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    """
    Generate AI-powered strategic suggestions for a team

    Args:
        league_id: Database league ID
        team_id: ESPN team ID
        current_user: Authenticated user
        db: Database session

    Returns:
        List of strategic suggestions
    """
    try:
        # Verify user has access to the league
        league_result = await db.execute(
            select(League).where(
                League.id == league_id,
                League.owner_user_id == current_user.id
            )
        )
        league = league_result.scalar_one_or_none()

        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found or access denied"
            )

        espn_service = ESPNService()

        # Get ESPN credentials
        cookies = None
        if league.espn_s2_encrypted or league.espn_swid_encrypted:
            s2 = ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None
            swid = ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
            if s2 or swid:
                cookies = ESPNCookies(espn_s2=s2, swid=swid)

        # Fetch team data
        try:
            roster_data = await espn_service.get_team_roster(
                str(league.espn_league_id),
                team_id,
                cookies=cookies
            )

            # Get league standings and settings
            league_data = await espn_service.get_league(
                str(league.espn_league_id),
                cookies=cookies
            )

            # Get recent matchups for context
            matchups_data = await espn_service.get_matchups(
                str(league.espn_league_id),
                week=None,  # Current week
                cookies=cookies
            )

            # Prepare data for LLM
            roster = roster_data.get("roster", [])
            league_info = {
                "name": league_data.get("name", "Unknown League"),
                "size": league_data.get("size", 10),
                "scoring_type": league_data.get("scoring_type", "standard"),
                "current_week": league_data.get("current_week", 1)
            }

            recent_matchups = matchups_data.get("matchups", [])[:5]

            # Generate suggestions using LLM
            suggestions = await llm_service.generate_strategic_suggestions(
                roster=roster,
                league_info=league_info,
                recent_matchups=recent_matchups,
                available_players=None  # Could add free agent data here
            )

            return [SuggestionResponse(**suggestion) for suggestion in suggestions]

        except ESPNError as e:
            logger.error("ESPN API error getting team data", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not fetch team data from ESPN: {str(e)}. Please check your ESPN credentials."
            )

    except HTTPException:
        raise
    except ESPNError as e:
        logger.error("ESPN API error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ESPN service unavailable: {str(e)}. Please try again later."
        )
    except Exception as e:
        logger.error("Failed to generate suggestions", error=str(e), exc_info=True)
        error_message = "Failed to generate AI suggestions. "
        if "api" in str(e).lower() or "groq" in str(e).lower() or "key" in str(e).lower():
            error_message += "AI service may be unavailable or not configured. Check your GROQ API key."
        else:
            error_message += "Please check your league settings and try again."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message
        )


@router.get("/health")
async def suggestions_health():
    """Check if suggestions service is available"""
    return {
        "llm_available": llm_service.is_available(),
        "model": llm_service.model if llm_service.is_available() else "not configured"
    }
