from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.db.database import get_database
from app.models.user import User
from app.models.league import League
from app.models.team import Team
from app.schemas.team import TeamResponse, RosterResponse
from app.core.auth import get_current_active_user
from app.services.espn_service import ESPNService, ESPNCookies, ESPNError
from app.utils.encryption import ESPNCredentialManager
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/league/{league_id}", response_model=List[TeamResponse])
async def get_league_teams(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        # Verify user has access to this league
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
        
        # Get teams from database
        teams_result = await db.execute(
            select(Team).where(Team.league_id == league_id)
        )
        teams = teams_result.scalars().all()
        
        return [TeamResponse.from_orm(team) for team in teams]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get league teams", league_id=league_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve teams"
        )


@router.get("/{team_id}/roster", response_model=RosterResponse)
async def get_team_roster(
    team_id: int,
    week: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        # Get team and verify access
        team_result = await db.execute(
            select(Team).where(Team.id == team_id)
        )
        team = team_result.scalar_one_or_none()
        
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        
        # Verify user has access to the league
        league_result = await db.execute(
            select(League).where(
                League.id == team.league_id,
                League.owner_user_id == current_user.id
            )
        )
        league = league_result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this team"
            )
        
        # Get roster from ESPN API
        espn_service = ESPNService()
        
        # Get ESPN credentials for the league
        cookies = None
        if league.espn_s2_encrypted or league.espn_swid_encrypted:
            s2 = ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None
            swid = ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
            if s2 or swid:
                cookies = ESPNCookies(espn_s2=s2, swid=swid)
        
        roster_data = await espn_service.get_team_roster(
            str(league.espn_league_id),
            team.espn_team_id,
            week,
            cookies
        )
        
        return RosterResponse(
            team_id=team_id,
            week=roster_data["week"],
            roster=roster_data["roster"]
        )
        
    except HTTPException:
        raise
    except ESPNError as e:
        logger.error("ESPN API error getting team roster", team_id=team_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ESPN service error: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to get team roster", team_id=team_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team roster"
        )


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        # Get team and verify access
        team_result = await db.execute(
            select(Team).where(Team.id == team_id)
        )
        team = team_result.scalar_one_or_none()
        
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        
        # Verify user has access to the league
        league_result = await db.execute(
            select(League).where(
                League.id == team.league_id,
                League.owner_user_id == current_user.id
            )
        )
        league = league_result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this team"
            )
        
        return TeamResponse.from_orm(team)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get team", team_id=team_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team"
        )