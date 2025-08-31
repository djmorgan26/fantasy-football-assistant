from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.db.database import get_database
from app.models.user import User
from app.models.league import League
from app.schemas.player import PlayerSearchRequest, PlayerSearchResponse
from app.core.auth import get_current_active_user
from app.services.espn_service import ESPNService, ESPNCookies, ESPNError
from app.utils.encryption import ESPNCredentialManager
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/players", tags=["players"])


@router.post("/search", response_model=PlayerSearchResponse)
async def search_players(
    search_request: PlayerSearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        # Verify user has access to the league
        league_result = await db.execute(
            select(League).where(
                League.id == search_request.league_id,
                League.owner_user_id == current_user.id
            )
        )
        league = league_result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found"
            )
        
        espn_service = ESPNService()
        
        # Get ESPN credentials for the league
        cookies = None
        if league.espn_s2_encrypted or league.espn_swid_encrypted:
            s2 = ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None
            swid = ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
            if s2 or swid:
                cookies = ESPNCookies(espn_s2=s2, swid=swid)
        
        # Get available players if requested, otherwise get all players from rosters
        if search_request.available_only:
            players = await espn_service.get_available_players(
                str(league.espn_league_id),
                search_request.week,
                search_request.position,
                cookies
            )
        else:
            # For now, we'll only support available players
            # Getting all rostered players would require fetching all team rosters
            players = await espn_service.get_available_players(
                str(league.espn_league_id),
                search_request.week,
                search_request.position,
                cookies
            )
        
        # Filter by search term if provided
        if search_request.search_term:
            search_term_lower = search_request.search_term.lower()
            players = [
                player for player in players
                if search_term_lower in player.get("full_name", "").lower()
            ]
        
        return PlayerSearchResponse(
            players=players,
            total_count=len(players)
        )
        
    except HTTPException:
        raise
    except ESPNError as e:
        logger.error("ESPN API error searching players", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ESPN service error: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to search players", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search players"
        )


@router.get("/league/{league_id}/available")
async def get_available_players(
    league_id: int,
    week: Optional[int] = None,
    position: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
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
                detail="League not found"
            )
        
        espn_service = ESPNService()
        
        # Get ESPN credentials
        cookies = None
        if league.espn_s2_encrypted or league.espn_swid_encrypted:
            s2 = ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None
            swid = ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
            if s2 or swid:
                cookies = ESPNCookies(espn_s2=s2, swid=swid)
        
        players = await espn_service.get_available_players(
            str(league.espn_league_id),
            week,
            position,
            cookies
        )
        
        return {
            "players": players,
            "total_count": len(players),
            "week": week,
            "position_filter": position
        }
        
    except HTTPException:
        raise
    except ESPNError as e:
        logger.error("ESPN API error getting available players", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ESPN service error: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to get available players", league_id=league_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available players"
        )