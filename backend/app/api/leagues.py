from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.database import get_database
from app.models.user import User
from app.models.league import League
from app.models.team import Team
from app.schemas.league import (
    LeagueConnectionRequest, 
    LeagueConnectionResponse, 
    LeagueResponse
)
from app.core.auth import get_current_active_user
from app.services.espn_service import ESPNService, ESPNCookies, ESPNError
from app.utils.encryption import ESPNCredentialManager
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/leagues", tags=["leagues"])


@router.post("/connect", response_model=LeagueConnectionResponse)
async def connect_league(
    connection_request: LeagueConnectionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        espn_service = ESPNService()
        
        # Create ESPN cookies object
        cookies = None
        if connection_request.espn_s2 or connection_request.espn_swid:
            cookies = ESPNCookies(
                espn_s2=connection_request.espn_s2,
                swid=connection_request.espn_swid
            )
        elif current_user.espn_s2_encrypted or current_user.espn_swid_encrypted:
            # Use user's stored credentials
            user_cookies = ESPNCredentialManager.get_espn_cookies_for_user(current_user)
            if user_cookies:
                cookies = ESPNCookies(
                    espn_s2=user_cookies.get("espn_s2"),
                    swid=user_cookies.get("SWID")
                )
        
        # Test connection and get league info
        league_info = await espn_service.get_league_info(
            str(connection_request.league_id),
            cookies
        )
        
        # Get team data
        teams_data = await espn_service.get_teams(
            str(connection_request.league_id),
            cookies
        )
        
        # Check if league already exists
        result = await db.execute(
            select(League).where(League.espn_league_id == connection_request.league_id)
        )
        existing_league = result.scalar_one_or_none()
        
        if existing_league:
            # Update existing league
            league = existing_league
            league.name = league_info["name"]
            league.size = league_info["size"]
            league.current_week = league_info["current_week"]
            league.scoring_type = league_info["scoring_type"]
            league.roster_settings = league_info["roster_settings"]
            league.scoring_settings = league_info["scoring_settings"]
            league.is_active = True  # Always set to active when connecting
        else:
            # Create new league
            league = League(
                espn_league_id=connection_request.league_id,
                name=league_info["name"],
                season_year=espn_service.season_year,
                size=league_info["size"],
                current_week=league_info["current_week"],
                scoring_type=league_info["scoring_type"],
                roster_settings=league_info["roster_settings"],
                scoring_settings=league_info["scoring_settings"],
                owner_user_id=current_user.id,
                is_active=True  # Always set to active when connecting
            )
            db.add(league)
        
        # Store encrypted credentials if provided
        if connection_request.espn_s2:
            league.espn_s2_encrypted = ESPNCredentialManager.encrypt_espn_s2(
                connection_request.espn_s2
            )
        if connection_request.espn_swid:
            league.espn_swid_encrypted = ESPNCredentialManager.encrypt_espn_swid(
                connection_request.espn_swid
            )
        
        await db.commit()
        await db.refresh(league)
        
        # Create/update teams
        for team_data in teams_data:
            result = await db.execute(
                select(Team).where(
                    Team.league_id == league.id,
                    Team.espn_team_id == team_data["id"]
                )
            )
            existing_team = result.scalar_one_or_none()
            
            if existing_team:
                # Update existing team
                team = existing_team
                team.name = team_data["name"]
                team.location = team_data["location"]
                team.nickname = team_data["nickname"]
                team.abbreviation = team_data["abbreviation"]
                team.logo_url = team_data["logo_url"]
                team.wins = team_data["wins"]
                team.losses = team_data["losses"]
                team.ties = team_data["ties"]
                team.points_for = team_data["points_for"]
                team.points_against = team_data["points_against"]
            else:
                # Create new team
                team = Team(
                    espn_team_id=team_data["id"],
                    league_id=league.id,
                    name=team_data["name"],
                    location=team_data["location"],
                    nickname=team_data["nickname"],
                    abbreviation=team_data["abbreviation"],
                    logo_url=team_data["logo_url"],
                    wins=team_data["wins"],
                    losses=team_data["losses"],
                    ties=team_data["ties"],
                    points_for=team_data["points_for"],
                    points_against=team_data["points_against"]
                )
                db.add(team)
        
        await db.commit()
        
        return LeagueConnectionResponse(
            success=True,
            message="League connected successfully",
            league=LeagueResponse.from_orm(league),
            teams=teams_data
        )
        
    except ESPNError as e:
        logger.error("ESPN API error during league connection", error=str(e))
        return LeagueConnectionResponse(
            success=False,
            message=f"ESPN connection failed: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected error during league connection", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect to league"
        )


@router.get("/", response_model=List[LeagueResponse])
async def get_user_leagues(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        result = await db.execute(
            select(League).where(
                League.owner_user_id == current_user.id,
                League.is_active == True
            )
        )
        leagues = result.scalars().all()
        return [LeagueResponse.from_orm(league) for league in leagues]
    except Exception as e:
        logger.error("Failed to get user leagues", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leagues"
        )


@router.get("/{league_id}", response_model=LeagueResponse)
async def get_league(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        result = await db.execute(
            select(League).where(
                League.id == league_id,
                League.owner_user_id == current_user.id
            )
        )
        league = result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found"
            )
        
        return LeagueResponse.from_orm(league)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get league", league_id=league_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league"
        )


@router.post("/{league_id}/sync", response_model=LeagueConnectionResponse)
async def sync_league(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        # Get the existing league
        result = await db.execute(
            select(League).where(
                League.id == league_id,
                League.owner_user_id == current_user.id
            )
        )
        league = result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found"
            )
        
        espn_service = ESPNService()
        
        # Get stored credentials if available
        cookies = None
        if league.espn_s2_encrypted or league.espn_swid_encrypted:
            # Create temporary cookies object from league credentials
            cookies = ESPNCookies(
                espn_s2=ESPNCredentialManager.decrypt_espn_s2(league.espn_s2_encrypted) if league.espn_s2_encrypted else None,
                swid=ESPNCredentialManager.decrypt_espn_swid(league.espn_swid_encrypted) if league.espn_swid_encrypted else None
            )
        
        # Fetch fresh league data
        league_info = await espn_service.get_league_info(
            str(league.espn_league_id),
            cookies
        )
        
        # Update league with fresh data
        league.name = league_info["name"]
        league.size = league_info["size"]
        league.current_week = league_info["current_week"]
        league.scoring_type = league_info["scoring_type"]
        league.roster_settings = league_info["roster_settings"]
        league.scoring_settings = league_info["scoring_settings"]
        league.last_synced = func.now()
        
        # Get fresh team data
        teams_data = await espn_service.get_teams(
            str(league.espn_league_id),
            cookies
        )
        
        # Update teams
        for team_data in teams_data:
            result = await db.execute(
                select(Team).where(
                    Team.league_id == league.id,
                    Team.espn_team_id == team_data["id"]
                )
            )
            existing_team = result.scalar_one_or_none()
            
            if existing_team:
                # Update existing team
                team = existing_team
                team.name = team_data["name"]
                team.location = team_data["location"]
                team.nickname = team_data["nickname"]
                team.abbreviation = team_data["abbreviation"]
                team.logo_url = team_data["logo_url"]
                team.wins = team_data["wins"]
                team.losses = team_data["losses"]
                team.ties = team_data["ties"]
                team.points_for = team_data["points_for"]
                team.points_against = team_data["points_against"]
            else:
                # Create new team
                team = Team(
                    espn_team_id=team_data["id"],
                    league_id=league.id,
                    name=team_data["name"],
                    location=team_data["location"],
                    nickname=team_data["nickname"],
                    abbreviation=team_data["abbreviation"],
                    logo_url=team_data["logo_url"],
                    wins=team_data["wins"],
                    losses=team_data["losses"],
                    ties=team_data["ties"],
                    points_for=team_data["points_for"],
                    points_against=team_data["points_against"]
                )
                db.add(team)
        
        await db.commit()
        await db.refresh(league)
        
        return LeagueConnectionResponse(
            success=True,
            message="League data synced successfully",
            league=LeagueResponse.from_orm(league),
            teams=teams_data
        )
        
    except ESPNError as e:
        logger.error("ESPN API error during league sync", error=str(e))
        return LeagueConnectionResponse(
            success=False,
            message=f"ESPN sync failed: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during league sync", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync league data"
        )


@router.delete("/{league_id}")
async def disconnect_league(
    league_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        result = await db.execute(
            select(League).where(
                League.id == league_id,
                League.owner_user_id == current_user.id
            )
        )
        league = result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found"
            )
        
        league.is_active = False
        await db.commit()
        
        return {"message": "League disconnected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to disconnect league", league_id=league_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect league"
        )