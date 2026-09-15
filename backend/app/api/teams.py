from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.db.database import get_database
from app.models.user import User
from app.models.league import League, PlatformType
from app.models.team import Team
from app.schemas.team import TeamResponse, RosterResponse
from app.core.auth import get_current_active_user
from app.services.espn_service import ESPNService, ESPNCookies, ESPNError
from app.utils.encryption import ESPNCredentialManager
from app.services.league_access import claimed_team_id, ensure_member, visible_to
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/teams", tags=["teams"])


def _team_response(team: Team, user_id: int, claimed_id: Optional[int]) -> TeamResponse:
    """`owner_user_id`, answered from the caller's point of view.

    The claim is per manager now (league_members.team_id), so a team co-owned by
    two people who both use the app reads as "yours" to each of them. The stored
    column is only the fallback for a league nobody has claimed a team in.
    """
    response = TeamResponse.from_orm(team)
    if claimed_id is not None:
        response.owner_user_id = user_id if team.id == claimed_id else None
    return response


async def _get_sleeper_team_roster(
    league: League, team: Team, week: Optional[int] = None
) -> List[dict]:
    """Build an ESPN-roster-shaped player list for a Sleeper team."""
    from app.services.sleeper_service import build_team_roster_entries, SleeperNotFoundError

    try:
        return await build_team_roster_entries(
            league.sleeper_league_id, team.sleeper_roster_id, week=week
        )
    except SleeperNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roster not found on Sleeper",
        )


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
                visible_to(current_user.id)
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
        
        claimed_id = await claimed_team_id(db, league_id, current_user.id)
        return [_team_response(team, current_user.id, claimed_id) for team in teams]
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
                visible_to(current_user.id)
            )
        )
        league = league_result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this team"
            )
        
        # Sleeper teams: build the roster from Sleeper data (the ESPN client
        # cannot serve them; league.espn_league_id is None).
        if league.platform == PlatformType.SLEEPER:
            roster = await _get_sleeper_team_roster(
                league, team, week=week or league.current_week
            )
            return RosterResponse(
                team_id=team_id,
                week=week or league.current_week or 1,
                roster=roster,
            )

        if league.platform == PlatformType.YAHOO:
            # Yahoo league discovery and standings are normalized today. Its
            # roster payload has a separate, deeply nested player schema and
            # must not accidentally be sent to ESPN while that adapter lands.
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Yahoo roster sync is not available yet; league and standings sync are available.",
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
                visible_to(current_user.id)
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


@router.put("/{team_id}/claim", response_model=TeamResponse)
async def claim_team(
    team_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    """Claim ownership of a team by the current user"""
    try:
        # Get team and verify it exists
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
                visible_to(current_user.id)
            )
        )
        league = league_result.scalar_one_or_none()
        
        if not league:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this league"
            )
        
        # Clear any existing team ownership for this user in this league
        clear_result = await db.execute(
            select(Team).where(
                Team.league_id == team.league_id,
                Team.owner_user_id == current_user.id
            )
        )
        existing_teams = clear_result.scalars().all()
        for existing_team in existing_teams:
            existing_team.owner_user_id = None

        # The claim lives on the membership, one per manager, because real
        # leagues have co-owned teams and `Team.owner_user_id` only holds one
        # user: claiming a team someone else had claimed used to take it from
        # them and their roster simply disappeared.
        membership = await ensure_member(db, team.league_id, current_user.id)
        membership.team_id = team.id

        # Keep the legacy column meaningful for whoever got there first, but
        # never take it from them.
        if team.owner_user_id is None:
            team.owner_user_id = current_user.id
        await db.commit()

        logger.info("Team claimed successfully", team_id=team_id, user_id=current_user.id)
        return _team_response(team, current_user.id, team.id)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to claim team", team_id=team_id, user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to claim team"
        )
