"""
Sleeper-specific league API endpoints
Handles Sleeper league connections, data retrieval, and synchronization
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.database import get_database
from app.models.user import User
from app.models.league import League, PlatformType
from app.models.team import Team
from app.models.matchup import Matchup
from app.schemas.sleeper import (
    SleeperLeagueConnectionRequest,
    SleeperLeagueConnectionResponse,
    SleeperUserLeaguesResponse
)
from app.schemas.league import LeagueResponse
from app.schemas.matchup import MatchupResponse
from app.core.auth import get_current_active_user
from app.services.sleeper_service import SleeperService, SleeperError, SleeperNotFoundError
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/sleeper", tags=["sleeper"])


@router.post("/connect", response_model=SleeperLeagueConnectionResponse)
async def connect_sleeper_league(
    connection_request: SleeperLeagueConnectionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    """
    Connect to a Sleeper league

    Args:
        connection_request: Contains league_id and user_id
        current_user: Authenticated user
        db: Database session

    Returns:
        League connection status and data
    """
    try:
        sleeper_service = SleeperService()

        # Validate user exists and get their leagues
        try:
            user_data = await sleeper_service.get_user(connection_request.sleeper_user_id)
        except SleeperNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sleeper user not found: {connection_request.sleeper_user_id}"
            )

        # Get league information
        try:
            league_data = await sleeper_service.get_league(connection_request.league_id)
        except SleeperNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"League not found: {connection_request.league_id}"
            )

        # Verify user is in the league
        is_member = await sleeper_service.validate_league_access(
            connection_request.league_id,
            user_data["user_id"]
        )

        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this league"
            )

        # Get rosters and users for team sync
        rosters = await sleeper_service.get_rosters(connection_request.league_id)
        league_users = await sleeper_service.get_league_users(connection_request.league_id)

        # Parse league settings
        scoring_settings = league_data.get("scoring_settings", {})
        roster_positions = league_data.get("roster_positions", [])

        # Determine scoring type
        ppr = scoring_settings.get("rec", 0)
        if ppr == 1:
            scoring_type = "ppr"
        elif ppr == 0.5:
            scoring_type = "half_ppr"
        else:
            scoring_type = "standard"

        # Check if league already exists
        result = await db.execute(
            select(League).where(
                League.sleeper_league_id == connection_request.league_id
            )
        )
        existing_league = result.scalar_one_or_none()

        if existing_league:
            # Update existing league
            league = existing_league
            league.name = league_data["name"]
            league.size = league_data["total_rosters"]
            league.season_year = int(league_data["season"])
            league.current_week = league_data.get("settings", {}).get("leg", 1)
            league.scoring_type = scoring_type
            league.roster_settings = {"roster_positions": roster_positions}
            league.scoring_settings = scoring_settings
            league.sleeper_user_id = user_data["user_id"]
            league.owner_user_id = current_user.id
            league.is_active = True
            league.platform = PlatformType.SLEEPER
        else:
            # Create new league
            league = League(
                platform=PlatformType.SLEEPER,
                sleeper_league_id=connection_request.league_id,
                sleeper_user_id=user_data["user_id"],
                name=league_data["name"],
                season_year=int(league_data["season"]),
                size=league_data["total_rosters"],
                current_week=league_data.get("settings", {}).get("leg", 1),
                scoring_type=scoring_type,
                roster_settings={"roster_positions": roster_positions},
                scoring_settings=scoring_settings,
                owner_user_id=current_user.id,
                is_active=True
            )
            db.add(league)

        await db.commit()
        await db.refresh(league)

        # Sync teams
        for roster in rosters:
            roster_id = roster["roster_id"]
            owner_id = roster.get("owner_id")

            # Find the user for this roster
            team_owner = next((u for u in league_users if u["user_id"] == owner_id), None)
            team_name = team_owner.get("display_name", f"Team {roster_id}") if team_owner else f"Team {roster_id}"

            # Check if team exists
            team_result = await db.execute(
                select(Team).where(
                    Team.league_id == league.id,
                    Team.sleeper_roster_id == roster_id
                )
            )
            existing_team = team_result.scalar_one_or_none()

            wins = roster.get("settings", {}).get("wins", 0)
            losses = roster.get("settings", {}).get("losses", 0)
            ties = roster.get("settings", {}).get("ties", 0)

            if existing_team:
                # Update existing team
                existing_team.name = team_name
                existing_team.wins = wins
                existing_team.losses = losses
                existing_team.ties = ties
                existing_team.points_for = roster.get("settings", {}).get("fpts", 0)
                existing_team.points_against = roster.get("settings", {}).get("fpts_against", 0)
            else:
                # Create new team
                team = Team(
                    league_id=league.id,
                    sleeper_roster_id=roster_id,
                    sleeper_owner_id=owner_id,
                    name=team_name,
                    wins=wins,
                    losses=losses,
                    ties=ties,
                    points_for=roster.get("settings", {}).get("fpts", 0),
                    points_against=roster.get("settings", {}).get("fpts_against", 0)
                )
                db.add(team)

        await db.commit()
        await db.refresh(league)

        logger.info(
            "Sleeper league connected",
            league_id=league.id,
            sleeper_league_id=connection_request.league_id,
            user_id=current_user.id
        )

        return SleeperLeagueConnectionResponse(
            success=True,
            message=f"Successfully connected to {league.name}",
            league_id=league.id,
            sleeper_league_id=league.sleeper_league_id,
            league_name=league.name,
            teams_synced=len(rosters)
        )

    except HTTPException:
        raise
    except SleeperError as e:
        logger.error("Sleeper API error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Sleeper API error: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to connect Sleeper league", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect league: {str(e)}"
        )


@router.get("/user/{user_identifier}/leagues/{season}", response_model=SleeperUserLeaguesResponse)
async def get_user_sleeper_leagues(
    user_identifier: str,
    season: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all Sleeper leagues for a user in a specific season

    Args:
        user_identifier: Sleeper username or user_id
        season: Year (e.g., 2024, 2025)

    Returns:
        List of leagues the user is in
    """
    try:
        sleeper_service = SleeperService()

        # Get user info first
        user_data = await sleeper_service.get_user(user_identifier)

        # Get all leagues for the season
        leagues = await sleeper_service.get_user_leagues(user_data["user_id"], season)

        logger.info(
            "Retrieved Sleeper leagues",
            user_id=user_data["user_id"],
            season=season,
            league_count=len(leagues)
        )

        return SleeperUserLeaguesResponse(
            user_id=user_data["user_id"],
            username=user_data.get("display_name", user_data.get("username", "Unknown")),
            season=season,
            leagues=leagues
        )

    except SleeperNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sleeper user not found: {user_identifier}"
        )
    except SleeperError as e:
        logger.error("Sleeper API error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Sleeper API error: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to get user leagues", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leagues"
        )


@router.get("/league/{league_id}/matchups/{week}", response_model=List[MatchupResponse])
async def get_sleeper_matchups(
    league_id: str,
    week: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    """
    Get Sleeper matchups for a specific week

    Args:
        league_id: Sleeper league ID
        week: Week number
        current_user: Authenticated user
        db: Database session

    Returns:
        List of matchup data
    """
    try:
        sleeper_service = SleeperService()

        # Verify league exists in our DB
        result = await db.execute(
            select(League).where(
                League.sleeper_league_id == league_id,
                League.owner_user_id == current_user.id
            )
        )
        league = result.scalar_one_or_none()

        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found or access denied"
            )

        # Get matchups from Sleeper
        matchups = await sleeper_service.get_matchups(league_id, week)

        logger.info(
            "Retrieved Sleeper matchups",
            league_id=league_id,
            week=week,
            matchup_count=len(matchups)
        )

        # Transform to MatchupResponse format
        # Note: Sleeper matchups are grouped by matchup_id
        matchup_responses = []
        for matchup in matchups:
            matchup_responses.append(MatchupResponse(
                roster_id=matchup["roster_id"],
                matchup_id=matchup.get("matchup_id"),
                points=matchup.get("points", 0),
                starters=matchup.get("starters", []),
                players=matchup.get("players", [])
            ))

        return matchup_responses

    except HTTPException:
        raise
    except SleeperError as e:
        logger.error("Sleeper API error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Sleeper API error: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to get matchups", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve matchups"
        )


@router.get("/league/{league_id}/rosters")
async def get_sleeper_rosters(
    league_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    """
    Get all rosters in a Sleeper league

    Args:
        league_id: Sleeper league ID
        current_user: Authenticated user
        db: Database session

    Returns:
        List of roster data
    """
    try:
        sleeper_service = SleeperService()

        # Verify league exists in our DB
        result = await db.execute(
            select(League).where(
                League.sleeper_league_id == league_id,
                League.owner_user_id == current_user.id
            )
        )
        league = result.scalar_one_or_none()

        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found or access denied"
            )

        # Get rosters from Sleeper
        rosters = await sleeper_service.get_rosters(league_id)

        logger.info(
            "Retrieved Sleeper rosters",
            league_id=league_id,
            roster_count=len(rosters)
        )

        return rosters

    except HTTPException:
        raise
    except SleeperError as e:
        logger.error("Sleeper API error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Sleeper API error: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to get rosters", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rosters"
        )


@router.get("/health")
async def sleeper_health():
    """Check if Sleeper API is reachable"""
    try:
        sleeper_service = SleeperService()
        # Try to get NFL state as a health check
        await sleeper_service._make_request("state/nfl")
        return {"status": "healthy", "service": "sleeper"}
    except Exception as e:
        return {"status": "unhealthy", "service": "sleeper", "error": str(e)}
